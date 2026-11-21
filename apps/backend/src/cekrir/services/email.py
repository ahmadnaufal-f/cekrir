"""Transactional email delivery through Resend or the existing SMTP transport."""

import smtplib
import ssl
from email.message import EmailMessage

import httpx

from cekrir.config import Settings


class EmailUnavailable(Exception):
    pass


def require_delivery_configuration(settings: Settings) -> None:
    if settings.email_provider == "resend":
        if not settings.resend_api_key or not settings.resend_api_key.get_secret_value().strip():
            raise EmailUnavailable("Resend is not configured")
        if not settings.resend_from or not settings.resend_from.strip():
            raise EmailUnavailable("Resend is not configured")
    elif not settings.smtp_host or not settings.smtp_from:
        raise EmailUnavailable("Email delivery is not configured")


def send_email(
    settings: Settings,
    recipient: str,
    subject: str,
    text: str,
    *,
    idempotency_key: str | None = None,
) -> None:
    require_delivery_configuration(settings)
    if settings.email_provider == "resend":
        headers = {"Authorization": f"Bearer {settings.resend_api_key.get_secret_value()}"}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        try:
            response = httpx.post(
                "https://api.resend.com/emails",
                headers=headers,
                json={
                    "from": settings.resend_from,
                    "to": [recipient],
                    "subject": subject,
                    "text": text,
                },
                timeout=10,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise EmailUnavailable("Email could not be sent") from exc
        return

    message = EmailMessage()
    message["From"] = settings.smtp_from
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(text)
    try:
        smtp_class = smtplib.SMTP_SSL if settings.smtp_security == "ssl" else smtplib.SMTP
        with smtp_class(settings.smtp_host, settings.smtp_port, timeout=10) as client:
            if settings.smtp_security == "starttls":
                client.starttls(context=ssl.create_default_context())
            if settings.smtp_username and settings.smtp_password:
                client.login(settings.smtp_username, settings.smtp_password.get_secret_value())
            client.send_message(message)
    except (OSError, smtplib.SMTPException) as exc:
        raise EmailUnavailable("Email could not be sent") from exc
