import os
from pathlib import Path
from urllib.parse import urlsplit

import psycopg
import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import select

from cekrir.config import Settings
from cekrir.db.model import Role, User
from cekrir.main import create_app
from cekrir.schemas import TrackingSnapshot
from cekrir.services.auth import issue_token


class FakeProvider:
    name = "test"

    def __init__(self):
        self.calls = 0
        self.status = "in_transit"
        self.fail = False
        self.history = []

    def lookup(self, resi_number: str, courier: str) -> TrackingSnapshot:
        from cekrir.services.tracking import TrackingUnavailable

        self.calls += 1
        if self.fail:
            raise TrackingUnavailable("Tracking provider is temporarily unavailable")
        return TrackingSnapshot(
            status=self.status, summary=f"Package {self.status}", history=self.history
        )


@pytest.fixture(scope="session")
def test_database_url():
    load_dotenv(Path(__file__).resolve().parents[3] / ".env")
    value = os.getenv("TEST_DATABASE_URL")
    if not value:
        raise pytest.UsageError("Set TEST_DATABASE_URL and run pnpm run db:test:deploy first")
    test_url = urlsplit(value)
    app_url = urlsplit(os.getenv("DATABASE_URL", ""))
    if test_url.scheme not in {"postgres", "postgresql"} or not test_url.path.endswith("_test"):
        raise pytest.UsageError("TEST_DATABASE_URL must be a PostgreSQL database ending in _test")
    if (test_url.hostname, test_url.port or 5432, test_url.path) == (
        app_url.hostname,
        app_url.port or 5432,
        app_url.path,
    ):
        raise pytest.UsageError("The test database must be separate from the application database")
    return value


@pytest.fixture
def database_url(test_database_url):
    # Only the explicitly configured, migrated test database is ever cleared.
    with psycopg.connect(test_database_url, autocommit=True) as connection:
        connection.execute("TRUNCATE notification, shipment")
    yield test_database_url
    with psycopg.connect(test_database_url, autocommit=True) as connection:
        connection.execute("TRUNCATE notification, shipment")


@pytest.fixture
def provider():
    return FakeProvider()


@pytest.fixture
def client(provider, database_url):
    settings = Settings(_env_file=None, DATABASE_URL=database_url, ingest_api_key="test-key")
    assert settings.database_url == database_url
    with TestClient(create_app(settings=settings, provider=provider)) as test_client:
        authorize_admin(test_client)
        yield test_client


def authorize_admin(client):
    with client.app.state.session_factory() as session:
        admin = session.scalar(
            select(User)
            .join(Role)
            .where(
                Role.code == "admin", User.is_active.is_(True), User.email_verified_at.is_not(None)
            )
        )
        assert admin is not None, "The test database needs an active, verified admin"
        token = issue_token(admin, client.app.state.settings, "access")
    client.headers["Authorization"] = f"Bearer {token}"
