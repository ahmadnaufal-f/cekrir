from uuid import UUID

from jwt import InvalidTokenError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from cekrir.config import Settings
from cekrir.db.model import User
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
from cekrir.services.email_verification import (
    EmailUnavailable,
    new_verification_token,
    prepare_verification,
    require_email_configuration,
    send_verification_email,
    verify_email,
)
from cekrir.validation.auth import CredentialsInput, RegisterInput


class AccountConflict(Exception):
    pass


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
    return token_response(user, settings)


def refresh_account(session: Session, settings: Settings, token: str) -> TokenRead:
    try:
        user_id = decode_token(token, settings, "refresh")
    except InvalidTokenError as exc:
        raise InvalidRefreshToken("Invalid or expired refresh token") from exc
    user = UserRepository(session).by_id(user_id)
    if user is None or not user.is_active or user.email_verified_at is None:
        raise InvalidRefreshToken("Invalid or expired refresh token")
    return token_response(user, settings)


def confirm_account_email(session: Session, token: str) -> None:
    if not verify_email(session, token):
        session.rollback()
        raise InvalidVerificationToken("Invalid or expired verification token")
    session.commit()


def resend_account_verification(
    session: Session, settings: Settings, payload: CredentialsInput
) -> None:
    require_email_configuration(settings)
    user = UserRepository(session).by_email(payload.email)
    if (
        user is None
        or user.email_verified_at is not None
        or not user.is_active
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
