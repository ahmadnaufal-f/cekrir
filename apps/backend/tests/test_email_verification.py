from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from cekrir.config import Settings
from cekrir.db.model import Role, User
from cekrir.db.session import build_engine, build_session_factory, get_session
from cekrir.middleware import RolePermissionMiddleware
from cekrir.routers.auth import router
from cekrir.services.accounts import register_account, resend_account_verification
from cekrir.services.email_verification import (
    EmailUnavailable,
    new_verification_token,
    prepare_verification,
    send_verification_email,
    token_hash,
    verify_email,
)
from cekrir.validation.auth import CredentialsInput, RegisterInput


def test_email_sends_single_use_token_over_starttls():
    settings = Settings(
        _env_file=None,
        smtp_host="smtp.example.test",
        smtp_from="test@example.test",
        verification_url="https://api.example.test/api/v1/auth/verify-email",
    )
    token = new_verification_token()
    with patch("cekrir.services.email.smtplib.SMTP") as smtp:
        send_verification_email(settings, "person@example.test", token)
        client = smtp.return_value.__enter__.return_value
        client.starttls.assert_called_once()
        message = client.send_message.call_args.args[0]
        assert message["To"] == "person@example.test"
        assert f"?token={token}" in message.get_content()
    assert token_hash(token) != token


def test_email_configuration_is_required():
    settings = Settings(_env_file=None)
    with pytest.raises(EmailUnavailable):
        send_verification_email(settings, "person@example.test", new_verification_token())


def test_token_is_single_use_and_expired_token_fails():
    token = new_verification_token()
    record = SimpleNamespace(user_id=uuid4(), expires_at=datetime.now(UTC) + timedelta(minutes=1))

    class FakeSession:
        current = record
        statement = None

        def scalar(self, statement):
            return self.current

        def execute(self, statement):
            self.statement = statement
            return SimpleNamespace(rowcount=1)

        def delete(self, value):
            self.current = None

    session = FakeSession()
    assert verify_email(session, token)
    assert session.statement.compile().params["is_active"] is True
    assert not verify_email(session, token)
    session.current = SimpleNamespace(
        user_id=uuid4(), expires_at=datetime.now(UTC) - timedelta(seconds=1)
    )
    assert not verify_email(session, token)


def test_unverified_user_cannot_sign_in():
    user = SimpleNamespace(email_verified_at=None, is_active=False, password_hash="unused")

    class FakeSession:
        def scalar(self, statement):
            return user

        def rollback(self):
            pass

    app = FastAPI()
    app.state.settings = Settings(_env_file=None)
    app.add_middleware(RolePermissionMiddleware)
    app.include_router(router)
    app.dependency_overrides[get_session] = lambda: FakeSession()
    response = TestClient(app).post(
        "/api/v1/auth/login", json={"email": "person@example.test", "password": "password"}
    )
    assert response.status_code == 401


def test_register_creates_inactive_user_and_keeps_it_when_delivery_fails():
    session = Mock()
    role = Role(id=uuid4(), code="member")
    payload = RegisterInput(
        email="person@example.test", full_name="Person", password="securepass123"
    )
    settings = Settings(_env_file=None)
    with (
        patch("cekrir.services.accounts.require_email_configuration"),
        patch("cekrir.services.accounts.UserRepository") as repository,
        patch("cekrir.services.accounts.hash_password", return_value="hashed"),
        patch("cekrir.services.accounts.prepare_verification"),
        patch("cekrir.services.accounts.send_verification_email", side_effect=EmailUnavailable),
        pytest.raises(EmailUnavailable, match="Account created"),
    ):
        repository.return_value.by_email.return_value = None
        repository.return_value.role_by_code.return_value = role
        register_account(session, settings, payload)
    assert session.add.call_args.args[0].is_active is False
    session.commit.assert_called_once()


def test_register_response_has_unassigned_location_and_device():
    app = FastAPI()
    app.state.settings = Settings(_env_file=None)
    app.include_router(router)
    app.dependency_overrides[get_session] = lambda: Mock()
    with patch("cekrir.routers.auth.accounts.register_account"):
        response = TestClient(app).post(
            "/api/v1/auth/register",
            json={
                "email": "person@example.test",
                "full_name": "Person",
                "password": "securepass123",
            },
        )
    assert response.status_code == 201
    assert response.json()["location_id"] is None
    assert response.json()["esp_device_id"] is None


def test_unverified_inactive_user_can_request_another_verification_email():
    user = SimpleNamespace(
        id=uuid4(),
        email="person@example.test",
        email_verified_at=None,
        is_active=False,
        password_hash="hash",
    )
    session = Mock()
    payload = CredentialsInput(email=user.email, password="secret")
    with (
        patch("cekrir.services.accounts.require_email_configuration"),
        patch("cekrir.services.accounts.UserRepository") as repository,
        patch("cekrir.services.accounts.verify_password", return_value=True),
        patch("cekrir.services.accounts.prepare_verification", return_value=True),
        patch("cekrir.services.accounts.send_verification_email") as send,
    ):
        repository.return_value.by_email.return_value = user
        resend_account_verification(session, Settings(_env_file=None), payload)
    assert send.call_args.args[1] == user.email
    session.commit.assert_called_once()


def test_verification_page_requires_explicit_confirmation():
    app = FastAPI()
    app.add_middleware(RolePermissionMiddleware)
    app.include_router(router)
    response = TestClient(app).get("/api/v1/auth/verify-email?token=example")
    assert response.status_code == 200
    assert "Verify email" in response.text
    assert response.headers["cache-control"] == "no-store"


def test_verification_is_single_use_with_concurrent_postgres_requests(database_url):
    engine = build_engine(database_url)
    sessions = build_session_factory(engine)
    user_id = uuid4()
    token = new_verification_token()
    try:
        with sessions.begin() as session:
            member = session.scalar(select(Role).where(Role.code == "member"))
            session.add(
                User(
                    id=user_id,
                    email=f"{user_id}@test.invalid",
                    full_name="Test",
                    password_hash="x",
                    role_record=member,
                    is_active=False,
                )
            )
            session.flush()
            assert prepare_verification(session, user_id, token)

        def confirm(_):
            with sessions.begin() as session:
                return verify_email(session, token)

        with ThreadPoolExecutor(max_workers=2) as pool:
            assert sorted(pool.map(confirm, range(2))) == [False, True]
        with sessions() as session:
            verified = session.get(User, user_id)
            assert verified.email_verified_at is not None
            assert verified.is_active is True
    finally:
        with sessions.begin() as session:
            session.execute(delete(User).where(User.id == user_id))
        engine.dispose()
