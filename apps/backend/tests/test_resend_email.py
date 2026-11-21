from unittest.mock import Mock, patch
from uuid import uuid4

import httpx
import pytest

from cekrir.config import Settings
from cekrir.services.accounts import InvalidVerificationToken, confirm_account_email
from cekrir.services.email import EmailUnavailable, send_email
from cekrir.services.email_verification import new_verification_token, send_verification_email


def resend_settings():
    return Settings(
        _env_file=None,
        email_provider="resend",
        resend_api_key="re_test_key",
        resend_from="Cekrir <mail@example.test>",
        verification_url="https://example.test/api/v1/auth/verify-email",
    )


def test_verification_is_sent_via_resend():
    token = new_verification_token()
    with patch("cekrir.services.email.httpx.post") as post:
        send_verification_email(resend_settings(), "user@example.test", token)
    kwargs = post.call_args.kwargs
    assert kwargs["json"]["to"] == ["user@example.test"]
    assert token in kwargs["json"]["text"]
    assert kwargs["headers"]["Authorization"] == "Bearer re_test_key"
    assert kwargs["headers"]["Idempotency-Key"].startswith("verification/")
    assert token not in kwargs["headers"]["Idempotency-Key"]
    post.return_value.raise_for_status.assert_called_once()


def test_resend_failure_is_reported_without_exposing_provider_response():
    response = Mock()
    response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "failure",
        request=httpx.Request("POST", "https://api.resend.com/emails"),
        response=httpx.Response(403),
    )
    with patch("cekrir.services.email.httpx.post", return_value=response):
        with pytest.raises(EmailUnavailable, match="Email could not be sent"):
            send_email(resend_settings(), "user@example.test", "Subject", "Message")


def test_resend_requires_a_sender_and_api_key():
    settings = Settings(_env_file=None, email_provider="resend")
    with pytest.raises(EmailUnavailable, match="not configured"):
        send_email(settings, "user@example.test", "Subject", "Message")


def test_welcome_email_sent_only_after_successful_verification():
    user_id = uuid4()
    session = Mock()
    session.get.return_value = Mock(email="member@example.test", full_name="Member")
    with (
        patch("cekrir.services.accounts.verify_email_user_id", return_value=user_id),
        patch("cekrir.services.accounts.send_email") as send,
    ):
        confirm_account_email(session, "token", resend_settings())
    session.commit.assert_called_once()
    assert send.call_args.args[1] == "member@example.test"
    assert send.call_args.kwargs["idempotency_key"] == f"welcome/{user_id}"

    with (
        patch("cekrir.services.accounts.verify_email_user_id", return_value=None),
        patch("cekrir.services.accounts.send_email") as send,
        pytest.raises(InvalidVerificationToken),
    ):
        confirm_account_email(session, "token", resend_settings())
    send.assert_not_called()
