from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import jwt
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from jwt import InvalidTokenError

from cekrir.config import Settings
from cekrir.db.session import get_session
from cekrir.middleware import RolePermissionMiddleware
from cekrir.routers.auth import router
from cekrir.services.auth import decode_token, issue_token


@pytest.fixture
def settings():
    return Settings(_env_file=None, jwt_secret_key="a" * 48)


@pytest.fixture
def user():
    return SimpleNamespace(
        id=uuid4(),
        email="person@example.com",
        full_name="Example Person",
        role="member",
        role_id=uuid4(),
        is_active=True,
        email_verified_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
    )


def test_token_claims_expiry_and_types(settings, user):
    for token_type, lifetime in [("access", 900), ("refresh", 604800)]:
        token = issue_token(user, settings, token_type)
        claims = jwt.decode(
            token,
            settings.jwt_secret_key.get_secret_value(),
            algorithms=["HS256"],
            issuer=settings.jwt_issuer,
        )
        assert (claims["email"], claims["full_name"], claims["role"]) == (
            user.email,
            user.full_name,
            user.role,
        )
        assert claims["exp"] - claims["iat"] == lifetime
        assert decode_token(token, settings, token_type) == user.id
        other_type = "refresh" if token_type == "access" else "access"
        with pytest.raises(InvalidTokenError):
            decode_token(token, settings, other_type)


def test_refresh_endpoint_checks_account_and_current_role(settings, user):
    class FakeSession:
        def get(self, model, user_id):
            return user if user_id == user.id else None

    app = FastAPI()
    app.state.settings = settings
    app.add_middleware(RolePermissionMiddleware)
    app.include_router(router)
    app.dependency_overrides[get_session] = lambda: FakeSession()
    client = TestClient(app)

    refresh_token = issue_token(user, settings, "refresh")
    user.role = "admin"
    response = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 200
    data = response.json()
    assert data["expires_in"] == 900
    assert data["refresh_expires_in"] == 604800
    assert data["user"]["role"] == "admin"
    assert decode_token(data["access_token"], settings, "access") == user.id
    claims = jwt.decode(
        data["access_token"],
        settings.jwt_secret_key.get_secret_value(),
        algorithms=["HS256"],
        issuer=settings.jwt_issuer,
    )
    assert claims["role"] == "admin"
    assert (
        client.post(
            "/api/v1/auth/refresh", json={"refresh_token": data["access_token"]}
        ).status_code
        == 401
    )
    user.is_active = False
    assert (
        client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token}).status_code
        == 401
    )


def test_expired_refresh_token_is_rejected(settings, user):
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "sub": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "token_type": "refresh",
            "iss": settings.jwt_issuer,
            "iat": now - timedelta(days=8),
            "exp": now - timedelta(days=1),
        },
        settings.jwt_secret_key.get_secret_value(),
        algorithm="HS256",
    )
    with pytest.raises(InvalidTokenError):
        decode_token(token, settings, "refresh")


def test_refresh_token_cannot_authorize_protected_route(settings, user):
    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def get(self, model, user_id):
            return user if user_id == user.id else None

        def scalars(self, statement):
            return ["shipments:read"]

    app = FastAPI()
    app.state.settings = settings
    app.state.session_factory = FakeSession
    app.add_middleware(RolePermissionMiddleware)

    @app.get("/api/v1/shipments")
    def shipments():
        return []

    client = TestClient(app)
    for token_type, expected in [("access", 200), ("refresh", 401)]:
        token = issue_token(user, settings, token_type)
        assert (
            client.get(
                "/api/v1/shipments", headers={"Authorization": f"Bearer {token}"}
            ).status_code
            == expected
        )


def test_permissions_are_loaded_from_database_for_each_request(settings, user):
    permissions = ["shipments:read"]

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def get(self, model, user_id):
            return user if user_id == user.id else None

        def scalars(self, statement):
            return permissions

    app = FastAPI()
    app.state.settings = settings
    app.state.session_factory = FakeSession
    app.add_middleware(RolePermissionMiddleware)

    @app.get("/api/v1/shipments")
    def shipments():
        return []

    client = TestClient(app)
    token = issue_token(user, settings, "access")
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/v1/shipments", headers=headers).status_code == 200
    permissions.clear()
    assert client.get("/api/v1/shipments", headers=headers).status_code == 403
