from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import delete

from cekrir.config import Settings
from cekrir.db.model import User
from cekrir.db.session import build_engine, build_session_factory, get_session
from cekrir.middleware import RolePermissionMiddleware
from cekrir.routers.auth import router
from cekrir.services.email_verification import (
    EmailUnavailable,
    new_verification_token,
    prepare_verification,
    send_verification_email,
    token_hash,
    verify_email,
)


def test_email_sends_single_use_token_over_starttls():
    settings = Settings(
        _env_file=None,
        smtp_host="smtp.example.test",
        smtp_from="test@example.test",
        verification_url="https://api.example.test/api/v1/auth/verify-email",
    )
    token = new_verification_token()
    with patch("cekrir.services.email_verification.smtplib.SMTP") as smtp:
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

        def scalar(self, statement):
            return self.current

        def execute(self, statement):
            pass

        def delete(self, value):
            self.current = None

    session = FakeSession()
    assert verify_email(session, token)
    assert not verify_email(session, token)
    session.current = SimpleNamespace(
        user_id=uuid4(), expires_at=datetime.now(UTC) - timedelta(seconds=1)
    )
    assert not verify_email(session, token)


def test_unverified_user_cannot_sign_in():
    user = SimpleNamespace(email_verified_at=None, is_active=True, password_hash="unused")

    class FakeSession:
        def scalar(self, statement):
            return user

        def rollback(self):
            pass

    app = FastAPI()
    app.add_middleware(RolePermissionMiddleware)
    app.include_router(router)
    app.dependency_overrides[get_session] = lambda: FakeSession()
    response = TestClient(app).post(
        "/api/v1/auth/login", json={"email": "person@example.test", "password": "password"}
    )
    assert response.status_code == 401


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
            session.add(
                User(
                    id=user_id,
                    email=f"{user_id}@test.invalid",
                    full_name="Test",
                    password_hash="x",
                    role="member",
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
            assert session.get(User, user_id).email_verified_at is not None
    finally:
        with sessions.begin() as session:
            session.execute(delete(User).where(User.id == user_id))
        engine.dispose()
