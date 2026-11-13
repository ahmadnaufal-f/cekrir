from datetime import UTC, datetime
from typing import Protocol

import httpx
from pydantic import ValidationError

from cekrir.config import Settings
from cekrir.schemas import TrackingEvent, TrackingSnapshot


class TrackingUnavailable(Exception):
    pass


class TrackingProvider(Protocol):
    name: str

    def lookup(self, resi_number: str, courier: str) -> TrackingSnapshot: ...


class DemoTrackingProvider:
    """Offline fixture: never contacts a courier or represents real tracking data."""

    name = "demo"

    def lookup(self, resi_number: str, courier: str) -> TrackingSnapshot:
        return TrackingSnapshot(
            status="in_transit",
            summary="Demo: package in transit. No courier API has been called.",
            history=[
                TrackingEvent(
                    occurred_at=datetime.now(UTC),
                    description="Demo barcode registered for tracking",
                    location="Demo sorting hub",
                )
            ],
        )


class HttpTrackingProvider:
    """Calls a normalized gateway; see docs/integrations.md for its contract."""

    name = "http"

    def __init__(self, settings: Settings):
        self.url = str(settings.tracking_api_url)
        self.headers = (
            {"Authorization": f"Bearer {settings.tracking_api_key.get_secret_value()}"}
            if settings.tracking_api_key
            else {}
        )

    def lookup(self, resi_number: str, courier: str) -> TrackingSnapshot:
        try:
            response = httpx.post(
                self.url,
                json={"resi_number": resi_number, "courier": courier},
                headers=self.headers,
                timeout=10.0,
                follow_redirects=False,
            )
            response.raise_for_status()
            return TrackingSnapshot.model_validate(response.json())
        except (httpx.HTTPError, ValidationError, ValueError) as exc:
            # Never surface upstream bodies, credentials, or request URLs to clients.
            raise TrackingUnavailable("Tracking provider is temporarily unavailable") from exc


def build_tracking_provider(settings: Settings) -> TrackingProvider:
    if settings.tracking_provider == "http":
        return HttpTrackingProvider(settings)
    return DemoTrackingProvider()
