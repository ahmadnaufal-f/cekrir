from collections.abc import Generator
from secrets import compare_digest

from fastapi import Header, HTTPException, Request

from cekrir.repository import ShipmentRepository
from cekrir.services.tracking import TrackingProvider


def get_repository(request: Request) -> Generator[ShipmentRepository, None, None]:
    with request.app.state.pool.connection() as connection:
        yield ShipmentRepository(connection)


def get_provider(request: Request) -> TrackingProvider:
    return request.app.state.tracking_provider


def require_ingest_key(request: Request, x_ingest_key: str | None = Header(default=None)) -> None:
    expected = request.app.state.settings.ingest_api_key
    if expected and not compare_digest(
        (x_ingest_key or "").encode(), expected.get_secret_value().encode()
    ):
        raise HTTPException(status_code=401, detail="Invalid ingestion key")
