from io import BytesIO
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from cekrir.config import Settings
from cekrir.main import create_app


def jpeg() -> bytes:
    output = BytesIO()
    Image.new("RGB", (80, 60), color="blue").save(output, format="JPEG")
    return output.getvalue()


class FakeCapture:
    def __init__(self, image: bytes, *, fail: bool = False):
        self.image = image
        self.fail = fail
        self.calls = 0

    def capture_jpeg(self) -> bytes:
        self.calls += 1
        if self.fail:
            raise RuntimeError("camera unavailable")
        return self.image


@pytest.fixture
def photo_client(database_url, provider, tmp_path):
    email = f"camera-{uuid4()}@example.test"
    password = "a long test password"
    settings = Settings(
        _env_file=None,
        DATABASE_URL=database_url,
        ingest_api_key="test-key",
        jwt_secret_key="a" * 48,
        bootstrap_admin_email=email,
        bootstrap_admin_password=password,
        cctv_photo_dir=tmp_path,
    )
    capture = FakeCapture(jpeg())
    app = create_app(settings=settings, provider=provider)
    app.state.photo_capturer = capture
    with TestClient(app) as client:
        login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
        assert login.status_code == 200
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        yield client, headers, capture, tmp_path


def test_detection_captures_once_and_serves_protected_photo(photo_client):
    client, auth, capture, directory = photo_client
    payload = {"resi_number": "PHOTO123", "courier": "jne", "camera_id": "esp32-door"}
    first = client.post("/api/v1/detections", json=payload, headers={"X-Ingest-Key": "test-key"})
    assert first.status_code == 200
    assert first.json()["shipment"]["photo_status"] == "pending"
    shipment_id = first.json()["shipment"]["id"]
    detail = client.get(f"/api/v1/shipments/{shipment_id}", headers=auth)
    assert detail.status_code == 200
    assert detail.json()["photo_status"] == "ready"
    assert detail.json()["photo_captured_at"] is not None
    photo_url = detail.json()["photo_url"]
    assert photo_url == f"/api/v1/shipments/{shipment_id}/photo"
    assert client.get(photo_url).status_code == 401
    photo = client.get(photo_url, headers=auth)
    assert photo.status_code == 200
    assert photo.content == capture.image
    assert photo.headers["content-type"] == "image/jpeg"
    assert photo.headers["cache-control"] == "private, no-store"
    assert (directory / f"{shipment_id}.jpg").read_bytes() == capture.image

    again = client.post("/api/v1/detections", json=payload, headers={"X-Ingest-Key": "test-key"})
    assert again.status_code == 200
    assert again.json()["created"] is False
    assert capture.calls == 1
    assert len(client.get("/api/v1/notifications", headers=auth).json()) == 1


def test_frame_detection_triggers_photo_and_failure_keeps_scan(photo_client, monkeypatch):
    client, auth, capture, _ = photo_client
    capture.fail = True
    monkeypatch.setattr("cekrir.services.detections.decode_frame", lambda _: ["FRAME123"])
    response = client.post(
        "/api/v1/detections/frame",
        params={"courier": "jne", "camera_id": "esp32-door"},
        content=jpeg(),
        headers={"Content-Type": "image/jpeg", "X-Ingest-Key": "test-key"},
    )
    assert response.status_code == 200
    assert response.json()["detected_count"] == 1
    shipment_id = response.json()["detections"][0]["shipment_id"]
    detail = client.get(f"/api/v1/shipments/{shipment_id}", headers=auth)
    assert detail.json()["photo_status"] == "unavailable"
    assert detail.json()["photo_url"] is None
    assert client.get(f"/api/v1/shipments/{shipment_id}/photo", headers=auth).status_code == 404
    assert len(client.get("/api/v1/notifications", headers=auth).json()) == 1
    assert capture.calls == 1
