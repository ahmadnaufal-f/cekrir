from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from uuid import uuid4

import psycopg
import pytest
from conftest import authorize_admin
from fastapi.testclient import TestClient
from sqlalchemy.exc import DBAPIError

from cekrir.config import Settings
from cekrir.main import create_app
from cekrir.schemas import TrackingEvent


def test_health(client):
    health = client.get("/health").json()
    assert health["status"] == "ok"
    assert health["tracking_provider"] == "demo"
    assert health["redis"] in {"ok", "unavailable"}


def test_manual_entry_normalizes_and_persists(client, provider):
    response = client.post(
        "/api/v1/shipments", json={"resi_number": " ab12345 ", "courier": " JNE "}
    )
    assert response.status_code == 201
    shipment = response.json()
    assert shipment["resi_number"] == "AB12345"
    assert shipment["courier"] == "jne"
    assert shipment["source"] == "manual"
    assert shipment["status"] == "in_transit"
    assert client.get("/api/v1/shipments").json() == [shipment]
    assert len(client.get("/api/v1/notifications").json()) == 1
    assert provider.calls == 1


def test_repeated_camera_frames_do_not_repeat_lookups_or_notifications(client, provider):
    payload = {"resi_number": "AB12345", "courier": "jne", "camera_id": "front-door"}
    first = client.post("/api/v1/detections", json=payload, headers={"X-Ingest-Key": "test-key"})
    second = client.post("/api/v1/detections", json=payload, headers={"X-Ingest-Key": "test-key"})
    assert first.status_code == second.status_code == 200
    assert first.json()["created"] is True
    assert second.json()["created"] is False
    assert first.json()["shipment"]["id"] == second.json()["shipment"]["id"]
    assert second.json()["shipment"]["last_detected_at"] is not None
    assert second.json()["shipment"]["status"] == "delivered"
    assert len(client.get("/api/v1/notifications").json()) == 1
    assert provider.calls == 0


def test_same_resi_on_different_couriers_is_distinct(client):
    for courier in ["jne", "jnt"]:
        assert (
            client.post(
                "/api/v1/shipments", json={"resi_number": "AB12345", "courier": courier}
            ).status_code
            == 201
        )
    assert len(client.get("/api/v1/shipments").json()) == 2


def test_status_changes_notify_once(client, provider):
    shipment = client.post(
        "/api/v1/shipments", json={"resi_number": "AB12345", "courier": "jne"}
    ).json()
    endpoint = f"/api/v1/shipments/{shipment['id']}/refresh"
    assert client.post(endpoint).status_code == 200
    assert len(client.get("/api/v1/notifications").json()) == 1
    provider.status = "delivered"
    assert client.post(endpoint).json()["status"] == "delivered"
    assert client.post(endpoint).status_code == 200
    assert len(client.get("/api/v1/notifications").json()) == 2


def test_failed_provider_does_not_create_partial_data(client, provider):
    provider.fail = True
    response = client.post("/api/v1/shipments", json={"resi_number": "AB12345", "courier": "jne"})
    assert response.status_code == 502
    assert client.get("/api/v1/shipments").json() == []
    assert client.get("/api/v1/notifications").json() == []


def test_failed_refresh_preserves_last_known_status(client, provider):
    shipment = client.post(
        "/api/v1/shipments", json={"resi_number": "AB12345", "courier": "jne"}
    ).json()
    provider.fail = True
    assert client.post(f"/api/v1/shipments/{shipment['id']}/refresh").status_code == 502
    assert client.get("/api/v1/shipments").json() == [shipment]
    assert len(client.get("/api/v1/notifications").json()) == 1


def test_ingestion_requires_configured_key(client):
    payload = {"resi_number": "AB12345", "courier": "jne", "camera_id": "front-door"}
    assert client.post("/api/v1/detections", json=payload).status_code == 401


def test_invalid_barcode_and_unknown_shipment(client):
    response = client.post(
        "/api/v1/shipments", json={"resi_number": "https://example.com", "courier": "jne"}
    )
    assert response.status_code == 422
    assert client.post("/api/v1/shipments/unknown/refresh").status_code == 404
    assert client.get("/api/v1/shipments?limit=0").status_code == 422


def test_database_survives_restart_and_concurrent_detections(database_url, provider):
    settings = Settings(_env_file=None, DATABASE_URL=database_url, ingest_api_key="test-key")
    payload = {"resi_number": "AB12345", "courier": "jne", "camera_id": "front-door"}
    with TestClient(create_app(settings=settings, provider=provider)) as client:
        authorize_admin(client)
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(
                pool.map(
                    lambda _: client.post(
                        "/api/v1/detections", json=payload, headers={"X-Ingest-Key": "test-key"}
                    ),
                    range(4),
                )
            )
        assert all(result.status_code == 200 for result in results)
        assert sum(result.json()["created"] for result in results) == 1
        assert len(client.get("/api/v1/notifications").json()) == 1
    with TestClient(create_app(settings=settings, provider=provider)) as client:
        authorize_admin(client)
        assert len(client.get("/api/v1/shipments").json()) == 1
        assert len(client.get("/api/v1/notifications").json()) == 1


def test_concurrent_status_refreshes_notify_once(client, provider):
    shipment = client.post(
        "/api/v1/shipments", json={"resi_number": "AB12345", "courier": "jne"}
    ).json()
    provider.status = "delivered"
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(
            pool.map(lambda _: client.post(f"/api/v1/shipments/{shipment['id']}/refresh"), range(4))
        )
    assert all(result.status_code == 200 for result in results)
    assert all(result.json()["status"] == "delivered" for result in results)
    assert len(client.get("/api/v1/notifications").json()) == 2


def test_history_and_timestamps_roundtrip_through_postgres(client, provider):
    provider.history = [
        TrackingEvent(
            occurred_at=datetime(2026, 11, 13, 8, 30, tzinfo=UTC),
            description="Arrived at sorting hub",
            location="Jakarta",
        )
    ]
    shipment = client.post(
        "/api/v1/shipments", json={"resi_number": "AB12345", "courier": "jne"}
    ).json()
    assert shipment["history"][0]["location"] == "Jakarta"
    assert shipment["history"][0]["occurred_at"] == "2026-11-13T08:30:00Z"
    assert datetime.fromisoformat(shipment["created_at"]).tzinfo is not None
    assert client.get("/api/v1/shipments").json() == [shipment]


def test_postgres_enforces_notification_foreign_key(database_url):
    with psycopg.connect(database_url, autocommit=True) as connection:
        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            connection.execute(
                "INSERT INTO notification (shipment_id, title, message) VALUES (%s, %s, %s)",
                (uuid4(), "Invalid reference", "Must not be persisted"),
            )


def test_notification_insert_failure_rolls_back_shipment(client, database_url):
    with psycopg.connect(database_url, autocommit=True) as connection:
        connection.execute(
            """CREATE FUNCTION reject_notification() RETURNS trigger LANGUAGE plpgsql AS $$
               BEGIN RAISE EXCEPTION 'Test notification failure'; END $$"""
        )
        connection.execute(
            """CREATE TRIGGER reject_notification BEFORE INSERT ON notification
               FOR EACH ROW EXECUTE FUNCTION reject_notification()"""
        )
        try:
            with pytest.raises(DBAPIError, match="Test notification failure") as failure:
                client.post("/api/v1/shipments", json={"resi_number": "AB12345", "courier": "jne"})
            assert isinstance(failure.value.orig, psycopg.errors.RaiseException)
            assert client.get("/api/v1/shipments").json() == []
            assert client.get("/api/v1/notifications").json() == []
        finally:
            connection.execute("DROP TRIGGER reject_notification ON notification")
            connection.execute("DROP FUNCTION reject_notification()")
