import os
from pathlib import Path
from urllib.parse import urlsplit

import psycopg
import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient

from cekrir.config import Settings
from cekrir.main import create_app
from cekrir.schemas import TrackingSnapshot


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
        raise pytest.UsageError("Set TEST_DATABASE_URL and run npm run db:test:deploy first")
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
        yield test_client
