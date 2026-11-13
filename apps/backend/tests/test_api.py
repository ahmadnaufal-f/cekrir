from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient
from sqlmodel import create_engine

from cekrir.config import Settings
from cekrir.main import create_app


def test_health(client):
    assert client.get("/health").json() == {"status": "ok", "tracking_provider": "demo"}


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
    assert len(client.get("/api/v1/notifications").json()) == 1
    assert provider.calls == 1


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


def test_database_survives_restart_and_concurrent_detections(tmp_path, provider):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'cekrir.db'}", connect_args={"check_same_thread": False}
    )
    settings = Settings(_env_file=None)
    payload = {"resi_number": "AB12345", "courier": "jne", "camera_id": "front-door"}
    with TestClient(create_app(settings=settings, engine=engine, provider=provider)) as client:
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(
                pool.map(lambda _: client.post("/api/v1/detections", json=payload), range(4))
            )
        assert all(result.status_code == 200 for result in results)
        assert sum(result.json()["created"] for result in results) == 1
        assert len(client.get("/api/v1/notifications").json()) == 1
    with TestClient(create_app(settings=settings, engine=engine, provider=provider)) as client:
        assert len(client.get("/api/v1/shipments").json()) == 1
        assert len(client.get("/api/v1/notifications").json()) == 1
    engine.dispose()
