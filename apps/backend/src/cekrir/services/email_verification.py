import hashlib
import logging
import secrets
import smtplib
import ssl
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from cekrir.config import Settings
from cekrir.db.model import EmailVerification, User

logger = logging.getLogger(__name__)
TOKEN_LIFETIME = timedelta(minutes=30)
RESEND_INTERVAL = timedelta(seconds=60)


class EmailUnavailable(Exception):
    pass


def require_email_configuration(settings: Settings) -> None:
    if not settings.smtp_host or not settings.smtp_from or not settings.verification_url:
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
    message = EmailMessage()
    message["From"] = settings.smtp_from
    message["To"] = recipient
    message["Subject"] = "Verify your Cekrir email"
    message.set_content(
        "Confirm your email address using this link within 30 minutes:\n\n"
        f"{verification_link(settings, token)}\n\n"
        "If you did not sign up, you can ignore this message."
    )
    try:
        smtp_class = smtplib.SMTP_SSL if settings.smtp_security == "ssl" else smtplib.SMTP
        with smtp_class(settings.smtp_host, settings.smtp_port, timeout=10) as client:
            if settings.smtp_security == "starttls":
                client.starttls(context=ssl.create_default_context())
            if settings.smtp_username and settings.smtp_password:
                client.login(settings.smtp_username, settings.smtp_password.get_secret_value())
            client.send_message(message)
    except (OSError, smtplib.SMTPException) as exc:
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


def verify_email(session: Session, token: str) -> bool:
    now = datetime.now(UTC)
    verification = session.scalar(
        select(EmailVerification)
        .where(EmailVerification.token_hash == token_hash(token))
        .with_for_update()
    )
    if verification is None or verification.expires_at <= now:
        return False
    session.execute(
        update(User).where(User.id == verification.user_id).values(email_verified_at=now)
    )
    session.delete(verification)
    return True
