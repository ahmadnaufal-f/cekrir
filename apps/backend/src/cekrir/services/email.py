"""Transactional email delivery through Resend or the existing SMTP transport."""

import smtplib
import ssl
from email.message import EmailMessage
from threading import Lock

import resend

from cekrir.config import Settings


class EmailUnavailable(Exception):
    pass


# The SDK stores its API key and HTTP client globally. Keep each call's
# configuration together when multiple request threads are sending email.
_resend_lock = Lock()


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
        try:
            with _resend_lock:
                old_key, old_client = resend.api_key, resend.default_http_client
                try:
                    resend.api_key = settings.resend_api_key.get_secret_value()
                    resend.default_http_client = resend.RequestsClient(timeout=10)
                    params = {
                        "from": settings.resend_from,
                        "to": [recipient],
                        "subject": subject,
                        "text": text,
                    }
                    options = {"idempotency_key": idempotency_key} if idempotency_key else None
                    resend.Emails.send(params, options)
                finally:
                    resend.api_key, resend.default_http_client = old_key, old_client
        except resend.exceptions.ResendError as exc:
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
