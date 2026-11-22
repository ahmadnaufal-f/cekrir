import logging
from uuid import UUID, uuid4

from jwt import InvalidTokenError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from cekrir.config import Settings
from cekrir.db.model import EspDevice, Location, LocationMember, User
from cekrir.db.repository import UserRepository
from cekrir.schemas import TokenRead, UserRead
from cekrir.services.auth import (
    ACCESS_TOKEN_LIFETIME,
    REFRESH_TOKEN_LIFETIME,
    decode_token,
    hash_password,
    issue_token,
    verify_password,
)
from cekrir.services.email import send_email
from cekrir.services.email_verification import (
    EmailUnavailable,
    new_verification_token,
    prepare_verification,
    require_email_configuration,
    send_verification_email,
    verify_email_user_id,
)
from cekrir.validation.auth import CredentialsInput, RegisterInput


class AccountConflict(Exception):
    pass


logger = logging.getLogger(__name__)


class InvalidCredentials(Exception):
    pass


class InvalidRefreshToken(Exception):
    pass


class InvalidVerificationToken(Exception):
    pass


class UserNotFound(Exception):
    pass


class RoleChangeConflict(Exception):
    pass


def token_response(user: User, settings: Settings) -> TokenRead:
    return TokenRead(
        access_token=issue_token(user, settings, "access"),
        refresh_token=issue_token(user, settings, "refresh"),
        expires_in=int(ACCESS_TOKEN_LIFETIME.total_seconds()),
        refresh_expires_in=int(REFRESH_TOKEN_LIFETIME.total_seconds()),
        user=UserRead.model_validate(user),
    )


def register_account(session: Session, settings: Settings, payload: RegisterInput) -> None:
    require_email_configuration(settings)
    repository = UserRepository(session)
    if repository.by_email(payload.email):
        session.rollback()
        raise AccountConflict("Email is already registered")
    session.rollback()
    user = User(
        email=payload.email,
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
        role_record=repository.role_by_code("member"),
        is_active=False,
    )
    session.add(user)
    token = new_verification_token()
    try:
        session.flush()
        prepare_verification(session, user.id, token)
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise AccountConflict("Email is already registered") from exc
    try:
        send_verification_email(settings, user.email, token)
    except EmailUnavailable as exc:
        raise EmailUnavailable(
            "Account created; retry sending the verification email later"
        ) from exc


def location_for_user(session: Session, user: User) -> tuple[UUID | None, str | None]:
    query = select(Location.id, EspDevice.device_id).outerjoin(
        EspDevice, EspDevice.location_id == Location.id
    )
    if user.role == "admin":
        query = query.where(Location.admin_user_id == user.id)
    else:
        query = query.join(LocationMember, LocationMember.location_id == Location.id).where(
            LocationMember.user_id == user.id
        )
    row = session.execute(query.order_by(Location.created_at, Location.id).limit(1)).first()
    return (row[0], row[1]) if row else (None, None)


def login_account(session: Session, settings: Settings, payload: CredentialsInput) -> TokenRead:
    user = UserRepository(session).by_email(payload.email)
    if (
        user is None
        or not user.is_active
        or user.email_verified_at is None
        or not verify_password(payload.password, user.password_hash)
    ):
        session.rollback()
        raise InvalidCredentials("Invalid email or password")
    location_id = None
    esp_device_id = None
    if user.role == "admin":
        # Serialize concurrent first logins so they reuse the same default setup.
        session.scalar(select(User.id).where(User.id == user.id).with_for_update())
        location = session.scalar(
            select(Location)
            .where(Location.admin_user_id == user.id)
            .order_by(Location.created_at, Location.id)
            .limit(1)
        )
        if location is None:
            location = Location(name="Main Location", admin=user)
            session.add(location)
            session.flush()
        esp = session.scalar(select(EspDevice).where(EspDevice.location_id == location.id))
        if esp is None:
            esp = EspDevice(device_id=str(uuid4()), location_id=location.id)
            session.add(esp)
            session.flush()
        location_id, esp_device_id = location.id, esp.device_id
        session.commit()
    else:
        location_id, esp_device_id = location_for_user(session, user)
    response = token_response(user, settings)
    response.location_id = location_id
    response.esp_device_id = esp_device_id
    return response


def refresh_account(session: Session, settings: Settings, token: str) -> TokenRead:
    try:
        user_id = decode_token(token, settings, "refresh")
    except InvalidTokenError as exc:
        raise InvalidRefreshToken("Invalid or expired refresh token") from exc
    user = UserRepository(session).by_id(user_id)
    if user is None or not user.is_active or user.email_verified_at is None:
        raise InvalidRefreshToken("Invalid or expired refresh token")
    response = token_response(user, settings)
    response.location_id, response.esp_device_id = location_for_user(session, user)
    return response


def confirm_account_email(session: Session, token: str, settings: Settings) -> None:
    user_id = verify_email_user_id(session, token)
    if user_id is None:
        session.rollback()
        raise InvalidVerificationToken("Invalid or expired verification token")
    user = session.get(User, user_id)
    recipient, name = user.email, user.full_name
    session.commit()
    try:
        send_email(
            settings,
            recipient,
            "Welcome to Cekrir",
            f"Hello {name},\n\nWelcome to Cekrir!",
            idempotency_key=f"welcome/{user_id}",
        )
    except EmailUnavailable:
        logger.warning("Welcome email could not be sent")


def resend_account_verification(
    session: Session, settings: Settings, payload: CredentialsInput
) -> None:
    require_email_configuration(settings)
    user = UserRepository(session).by_email(payload.email)
    if (
        user is None
        or user.email_verified_at is not None
        or not verify_password(payload.password, user.password_hash)
    ):
        session.rollback()
        return
    user_id, email = user.id, user.email
    token = new_verification_token()
    prepared = prepare_verification(session, user_id, token)
    session.commit()
    if prepared:
        send_verification_email(settings, email, token)


def list_accounts(session: Session) -> list[UserRead]:
    return [UserRead.model_validate(user) for user in UserRepository(session).list_users()]


def change_role(session: Session, user_id: UUID, role: str) -> UserRead:
    repository = UserRepository(session)
    user = repository.by_id(user_id)
    if user is None:
        session.rollback()
        raise UserNotFound("User not found")
    user.role_record = repository.role_by_code(role)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise RoleChangeConflict(
            "Reassign the user's locations before changing their role"
        ) from exc
    return UserRead.model_validate(user)
