from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import UUID

import bcrypt
import jwt
from jwt import InvalidTokenError
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from cekrir.config import Settings
from cekrir.db.model import Permission, RolePermission, User
from cekrir.db.repository import UserRepository


def hash_password(password: str) -> str:
    encoded = password.encode("utf-8")
    if len(encoded) > 72:
        raise ValueError("Password must be no more than 72 UTF-8 bytes")
    return bcrypt.hashpw(encoded, bcrypt.gensalt(rounds=12)).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    encoded = password.encode("utf-8")
    if len(encoded) > 72:
        return False
    try:
        return bcrypt.checkpw(encoded, password_hash.encode("ascii"))
    except (ValueError, TypeError):
        return False


ACCESS_TOKEN_LIFETIME = timedelta(minutes=15)
REFRESH_TOKEN_LIFETIME = timedelta(days=7)
TokenType = Literal["access", "refresh"]


def issue_token(user: User, settings: Settings, token_type: TokenType) -> str:
    now = datetime.now(UTC)
    lifetime = ACCESS_TOKEN_LIFETIME if token_type == "access" else REFRESH_TOKEN_LIFETIME
    return jwt.encode(
        {
            "sub": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "token_type": token_type,
            "iss": settings.jwt_issuer,
            "iat": now,
            "exp": now + lifetime,
        },
        settings.jwt_secret_key.get_secret_value(),
        algorithm="HS256",
    )


def decode_token(token: str, settings: Settings, expected_type: TokenType) -> UUID:
    claims = jwt.decode(
        token,
        settings.jwt_secret_key.get_secret_value(),
        algorithms=["HS256"],
        issuer=settings.jwt_issuer,
        options={
            "require": ["sub", "iss", "iat", "exp", "email", "full_name", "role", "token_type"]
        },
    )
    if claims["token_type"] != expected_type:
        raise InvalidTokenError("Invalid token type")
    try:
        return UUID(claims["sub"])
    except (ValueError, TypeError, AttributeError) as exc:
        raise InvalidTokenError("Invalid token subject") from exc


def authenticate_token(token: str, settings: Settings, session_factory: sessionmaker[Session]):
    try:
        user_id = decode_token(token, settings, "access")
    except (InvalidTokenError, ValueError):
        return None
    with session_factory() as session:
        user = UserRepository(session).by_id(user_id)
        if user is None or not user.is_active or user.email_verified_at is None:
            return None
        permissions = set(
            session.scalars(
                select(Permission.code)
                .join(RolePermission, RolePermission.permission_id == Permission.id)
                .where(RolePermission.role_id == user.role_id)
            )
        )
        return {
            "id": str(user.id),
            "email": user.email,
            "role": user.role,
            "permissions": permissions,
        }


def ensure_bootstrap_admin(session_factory: sessionmaker[Session], settings: Settings) -> None:
    if not settings.bootstrap_admin_email or not settings.bootstrap_admin_password:
        return
    email = settings.bootstrap_admin_email.strip().lower()
    with session_factory() as session, session.begin():
        repository = UserRepository(session)
        if repository.by_email(email) is None:
            session.add(
                User(
                    email=email,
                    full_name=settings.bootstrap_admin_full_name.strip(),
                    password_hash=hash_password(
                        settings.bootstrap_admin_password.get_secret_value()
                    ),
                    role_record=repository.role_by_code("admin"),
                    email_verified_at=datetime.now(UTC),
                    is_active=True,
                )
            )
