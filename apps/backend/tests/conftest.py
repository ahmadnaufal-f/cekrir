import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import create_engine

from cekrir.config import Settings
from cekrir.main import create_app
from cekrir.schemas import TrackingSnapshot


class FakeProvider:
    name = "test"
    calls = 0
    status = "in_transit"
    fail = False

    def lookup(self, resi_number: str, courier: str) -> TrackingSnapshot:
        from cekrir.services.tracking import TrackingUnavailable

        self.calls += 1
        if self.fail:
            raise TrackingUnavailable("Tracking provider is temporarily unavailable")
        return TrackingSnapshot(status=self.status, summary=f"Package {self.status}")


@pytest.fixture
def provider():
    return FakeProvider()


@pytest.fixture
def client(provider):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    settings = Settings(_env_file=None, ingest_api_key="test-key")
    with TestClient(create_app(settings=settings, engine=engine, provider=provider)) as test_client:
        yield test_client
    engine.dispose()
