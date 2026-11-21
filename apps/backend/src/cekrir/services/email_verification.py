import hashlib
import logging
import secrets
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from cekrir.config import Settings
from cekrir.db.model import EmailVerification, User
from cekrir.services.email import EmailUnavailable, require_delivery_configuration, send_email

logger = logging.getLogger(__name__)
TOKEN_LIFETIME = timedelta(minutes=30)
RESEND_INTERVAL = timedelta(seconds=60)


def require_email_configuration(settings: Settings) -> None:
    require_delivery_configuration(settings)
    if not settings.verification_url:
        raise EmailUnavailable("Email verification is not configured")


def new_verification_token() -> str:
    return secrets.token_urlsafe(32)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("ascii")).hexdigest()


def verification_link(settings: Settings, token: str) -> str:
    parts = urlsplit(str(settings.verification_url))
    query = [(key, value) for key, value in parse_qsl(parts.query) if key != "token"]
    query.append(("token", token))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def send_verification_email(settings: Settings, recipient: str, token: str) -> None:
    require_email_configuration(settings)
    try:
        send_email(
            settings,
            recipient,
            "Verify your Cekrir email",
            "Confirm your email address using this link within 30 minutes:\n\n"
            f"{verification_link(settings, token)}\n\n"
            "If you did not sign up, you can ignore this message.",
            idempotency_key=f"verification/{token_hash(token)}",
        )
    except EmailUnavailable as exc:
        logger.warning("Verification email delivery failed")
        raise EmailUnavailable("Verification email could not be sent") from exc


def prepare_verification(session: Session, user_id: UUID, token: str) -> bool:
    now = datetime.now(UTC)
    verification = session.scalar(
        select(EmailVerification).where(EmailVerification.user_id == user_id).with_for_update()
    )
    if verification and now - verification.sent_at < RESEND_INTERVAL:
        return False
    if verification is None:
        verification = EmailVerification(user_id=user_id)
        session.add(verification)
    verification.token_hash = token_hash(token)
    verification.sent_at = now
    verification.expires_at = now + TOKEN_LIFETIME
    return True


def verify_email_user_id(session: Session, token: str) -> UUID | None:
    now = datetime.now(UTC)
    verification = session.scalar(
        select(EmailVerification)
        .where(EmailVerification.token_hash == token_hash(token))
        .with_for_update()
    )
    if verification is None or verification.expires_at <= now:
        return None
    session.execute(
        update(User).where(User.id == verification.user_id).values(email_verified_at=now)
    )
    user_id = verification.user_id
    session.delete(verification)
    return user_id


def verify_email(session: Session, token: str) -> bool:
    return verify_email_user_id(session, token) is not None
