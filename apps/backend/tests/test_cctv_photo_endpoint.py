from io import BytesIO
from uuid import UUID, uuid4

import pytest
from cryptography.fernet import Fernet
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
        self.calls: list[str] = []

    def capture_jpeg(self, device_id: str) -> bytes:
        self.calls.append(device_id)
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
        cctv_encryption_key=Fernet.generate_key().decode(),
        tuya_api_key="test-tuya-key",
        tuya_api_endpoint="https://tuya.example.test",
        tuya_cctv_device_id="legacy-camera",
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
    assert capture.calls == ["legacy-camera"]
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
    assert capture.calls == ["legacy-camera"]


def test_selected_delivery_camera_follows_the_esp_location(photo_client, monkeypatch):
    client, auth, capture, _ = photo_client
    location = client.get("/api/v1/locations", headers=auth).json()[0]["id"]
    other_login = client.post(
        "/api/v1/auth/login",
        json={
            "email": "seed-admin@example.test",
            "password": "isolated-test-admin-password",
        },
    ).json()
    other_auth = {"Authorization": f"Bearer {other_login['access_token']}"}
    other_location = other_login["location_id"]
    client.app.state.settings.tuya_location_devices = {
        UUID(location): {"front-tuya", "side-tuya"},
        UUID(other_location): {"other-tuya"},
    }
    cameras = f"/api/v1/locations/{location}/cctv"
    payload = {
        "name": "Front",
        "stream_url": "rtsp://192.168.1.20",
        "username": "admin",
        "password": "private",
    }
    response = client.post(cameras, headers=auth, json=payload)
    assert response.status_code == 201
    front = response.json()["id"]
    assert client.put(f"{cameras}/{front}/delivery", headers=auth).status_code == 409
    assert (
        client.patch(
            f"{cameras}/{front}",
            headers=auth,
            json={
                "name": "Front",
                "tuya_device_id": "other-tuya",
            },
        ).status_code
        == 409
    )
    linked = client.patch(
        f"{cameras}/{front}",
        headers=auth,
        json={
            "name": "Front",
            "tuya_device_id": "front-tuya",
        },
    )
    assert linked.status_code == 200
    assert linked.json()["tuya_device_id"] == "front-tuya"
    side = client.post(
        cameras,
        headers=auth,
        json={
            **payload,
            "name": "Side",
            "tuya_device_id": "side-tuya",
        },
    ).json()["id"]
    assert client.put(f"{cameras}/{side}/delivery", headers=other_auth).status_code == 404
    assert (
        client.put(
            f"/api/v1/locations/{other_location}/cctv/{side}/delivery",
            headers=other_auth,
        ).status_code
        == 404
    )

    worker = client.post(f"/api/v1/locations/{location}/esp/credentials", headers=auth).json()
    resi = "UNSELECTED123"
    monkeypatch.setattr("cekrir.services.detections.decode_frame", lambda _: [resi])
    params = {"courier": "jne"}
    headers = {"Content-Type": "image/jpeg", "X-Device-Key": worker["device_key"]}
    frames = f"/api/v1/devices/{worker['device_id']}/frames"
    scan = client.post(frames, params=params, content=jpeg(), headers=headers)
    assert scan.status_code == 200
    assert capture.calls == []

    for camera_id, device_id, tracking in [
        (front, "front-tuya", "FRONT123"),
        (side, "side-tuya", "SIDE123"),
    ]:
        selected = client.put(f"{cameras}/{camera_id}/delivery", headers=auth)
        assert selected.status_code == 200
        assert selected.json()["is_delivery_camera"] is True
        assert [
            entry["id"]
            for entry in client.get(cameras, headers=auth).json()
            if entry["is_delivery_camera"]
        ] == [camera_id]
        resi = tracking
        scan = client.post(frames, params=params, content=jpeg(), headers=headers)
        assert scan.status_code == 200
        assert capture.calls[-1] == device_id
        shipment_id = scan.json()["detections"][0]["shipment_id"]
        photo_url = f"/api/v1/shipments/{shipment_id}/photo"
        assert client.get(photo_url, headers=auth).content == capture.image
        assert client.get(photo_url, headers=other_auth).status_code == 404
    assert capture.calls == ["front-tuya", "side-tuya"]
