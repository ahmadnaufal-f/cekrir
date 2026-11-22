import json
from datetime import UTC, datetime
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet
from pydantic import SecretStr

from cekrir.config import Settings
from cekrir.db.model import CctvCamera
from cekrir.schemas import NotificationRead
from cekrir.services import binderbyte, devices
from cekrir.services.push_notifications import PushNotificationPublisher
from cekrir.validation.devices import CctvCreate
from cekrir.validation.tracking import BinderByteInput


def test_binderbyte_sanitizes_errors_and_passes_parameters():
    settings = Settings(_env_file=None, binderbyte_api_key="private-key")
    payload = BinderByteInput(courier="jne", resi_number="ABC123", phone_last_five="12345")
    connection = Mock()
    response = connection.getresponse.return_value
    response.status = 200
    response.read.return_value = json.dumps(
        {
            "status": 200,
            "data": {
                "summary": {"status": "DELIVERED"},
                "detail": {"receiver": "A"},
                "history": [],
            },
        }
    ).encode()
    with patch("cekrir.services.binderbyte.http.client.HTTPSConnection", return_value=connection):
        result = binderbyte.check_tracking(settings, payload)
        assert result["summary"]["status"] == "DELIVERED"
        assert "api_key=private-key" in connection.request.call_args.args[1]
        response.status = 403
        with pytest.raises(binderbyte.BinderByteUnavailable) as error:
            binderbyte.check_tracking(settings, payload)
        assert "private-key" not in str(error.value)
    connection.close.assert_called()


def test_cctv_encrypts_credentials_and_never_returns_them():
    key = Fernet.generate_key()
    settings = Settings(_env_file=None, cctv_encryption_key=key.decode())
    payload = CctvCreate(
        name="Front", stream_url="rtmps://camera.test/live", username="camuser", password="private"
    )
    session = Mock()

    def assign_id(camera):
        camera.id = uuid4()

    session.add.side_effect = assign_id
    with patch("cekrir.services.devices._owned_location"):
        result = devices.add_cctv(session, settings, uuid4(), uuid4(), payload)
    camera = session.add.call_args.args[0]
    assert isinstance(camera, CctvCamera)
    assert "private" not in camera.password_encrypted
    assert Fernet(key).decrypt(camera.password_encrypted.encode()) == b"private"
    assert "password" not in result and "stream_url" not in result and "username" not in result


def test_cctv_rejects_credentials_in_url():
    with pytest.raises(ValueError):
        CctvCreate(
            name="Front", stream_url="rtmp://user:pass@host/live", username="u", password="p"
        )


def test_fcm_sends_arrival_notifications_and_skips_other_events():
    settings = Settings(_env_file=None, firebase_credentials_file="fake-credentials.json")
    session = Mock()
    session.scalar.return_value = uuid4()
    session.scalars.return_value = iter(["token-a", "token-b"])
    factory = Mock()
    factory.return_value.__enter__ = Mock(return_value=session)
    factory.return_value.__exit__ = Mock(return_value=False)
    publisher = PushNotificationPublisher(settings, factory)
    notification = NotificationRead(
        id=uuid4(),
        shipment_id=uuid4(),
        title="Package arrived",
        message="Package delivered",
        created_at=datetime.now(UTC),
    )
    with (
        patch.object(publisher, "_app", return_value=Mock()),
        patch("cekrir.services.push_notifications.messaging.send_each_for_multicast") as send,
    ):
        send.return_value.failure_count = 0
        publisher.publish(notification)
        assert send.call_args.args[0].tokens == ["token-a", "token-b"]
        notification.title = "Package added"
        publisher.publish(notification)
        send.assert_called_once()


def test_login_provision_device_and_register_fcm(client, database_url):
    credentials = {"email": "seed-admin@example.test", "password": "isolated-test-admin-password"}
    first = client.post("/api/v1/auth/login", json=credentials)
    second = client.post("/api/v1/auth/login", json=credentials)
    assert first.status_code == second.status_code == 200
    login = first.json()
    assert (login["location_id"], login["esp_device_id"]) == (
        second.json()["location_id"],
        second.json()["esp_device_id"],
    )
    headers = {"Authorization": f"Bearer {login['access_token']}"}
    location_id = login["location_id"]
    refreshed = client.post("/api/v1/auth/refresh", json={"refresh_token": login["refresh_token"]})
    assert refreshed.status_code == 200
    assert (refreshed.json()["location_id"], refreshed.json()["esp_device_id"]) == (
        location_id, login["esp_device_id"]
    )
    listed = client.get("/api/v1/locations", headers=headers).json()
    matching_location = next(item for item in listed if item["id"] == location_id)
    assert matching_location["esp_device_id"] == login["esp_device_id"]
    result = client.post(f"/api/v1/locations/{location_id}/esp/credentials", headers=headers)
    assert result.status_code == 200
    assert result.headers["cache-control"] == "no-store"
    device_id, key = result.json()["device_id"], result.json()["device_key"]
    assert device_id == login["esp_device_id"]
    # Authorization is checked before attempting to decode a JPEG.
    url = f"/api/v1/devices/{device_id}/frames?courier=jne"
    assert client.post(url, content=b"x", headers={"Content-Type": "image/jpeg"}).status_code == 401
    assert (
        client.post(
            url, content=b"x", headers={"Content-Type": "image/jpeg", "X-Device-Key": "bad"}
        ).status_code
        == 401
    )
    assert (
        client.post(
            url, content=b"x", headers={"Content-Type": "image/jpeg", "X-Device-Key": key}
        ).status_code
        == 422
    )
    # A valid device credential updates its online state even if the frame is invalid.
    assert (
        next(
            item
            for item in client.get("/api/v1/locations", headers=headers).json()
            if item["id"] == location_id
        )["onboarding_complete"]
        is True
    )
    replacement = client.post(f"/api/v1/locations/{location_id}/esp/credentials", headers=headers)
    assert replacement.status_code == 200
    assert (
        client.post(
            url, content=b"x", headers={"Content-Type": "image/jpeg", "X-Device-Key": key}
        ).status_code
        == 401
    )
    assert (
        client.post(
            url,
            content=b"x",
            headers={
                "Content-Type": "image/jpeg",
                "X-Device-Key": replacement.json()["device_key"],
            },
        ).status_code
        == 422
    )
    push = client.post(
        "/api/v1/notifications/fcm",
        headers=headers,
        json={"location_id": location_id, "token": f"test-token-{uuid4()}"},
    )
    assert push.status_code == 200
    assert "token" not in push.json()
    device = push.json()["device_id"]
    assert client.delete(f"/api/v1/notifications/fcm/{device}", headers=headers).status_code == 200

    member_login = client.post(
        "/api/v1/auth/login",
        json={"email": "seed-member@example.test", "password": "isolated-test-member-password"},
    ).json()
    assert member_login["location_id"] is None
    assert member_login["esp_device_id"] is None
    member_headers = {"Authorization": f"Bearer {member_login['access_token']}"}
    member_id = member_login["user"]["id"]
    member_payload = {"location_id": location_id, "token": f"member-token-{uuid4()}"}
    assert (
        client.post(
            "/api/v1/notifications/fcm", headers=member_headers, json=member_payload
        ).status_code
        == 404
    )
    assert (
        client.put(
            f"/api/v1/locations/{location_id}/members/{member_id}", headers=headers
        ).status_code
        == 200
    )
    member_again = client.post(
        "/api/v1/auth/login",
        json={"email": "seed-member@example.test", "password": "isolated-test-member-password"},
    ).json()
    assert (member_again["location_id"], member_again["esp_device_id"]) == (
        location_id, login["esp_device_id"]
    )
    member_refresh = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": member_again["refresh_token"]}
    ).json()
    assert (member_refresh["location_id"], member_refresh["esp_device_id"]) == (
        location_id, login["esp_device_id"]
    )
    assert (
        client.post(
            "/api/v1/notifications/fcm", headers=member_headers, json=member_payload
        ).status_code
        == 200
    )

    client.app.state.settings.cctv_encryption_key = SecretStr(Fernet.generate_key().decode())
    cctv = {
        "name": "Front",
        "stream_url": "rtmp://camera.local/live",
        "username": "user",
        "password": "secret",
    }
    created = client.post(f"/api/v1/locations/{location_id}/cctv", headers=headers, json=cctv)
    assert created.status_code == 201
    assert "password" not in created.json() and "stream_url" not in created.json()
    assert len(client.get(f"/api/v1/locations/{location_id}/cctv", headers=headers).json()) == 1


def test_existing_package_detected_updates_status_only(client, provider):
    created = client.post(
        "/api/v1/shipments", json={"resi_number": "AA12345", "courier": "jne"}
    ).json()
    response = client.post(
        "/api/v1/detections",
        headers={"X-Ingest-Key": "test-key"},
        json={"resi_number": "AA12345", "courier": "jne", "camera_id": "front-door"},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["created"] is False
    assert result["shipment"]["id"] == created["id"]
    assert result["shipment"]["status"] == "delivered"
    assert result["shipment"]["summary"] == created["summary"]
    assert result["shipment"]["history"] == created["history"]
    assert provider.calls == 1
    assert len(client.get("/api/v1/notifications").json()) == 2
    client.post(
        "/api/v1/detections",
        headers={"X-Ingest-Key": "test-key"},
        json={"resi_number": "AA12345", "courier": "jne", "camera_id": "front-door"},
    )
    assert len(client.get("/api/v1/notifications").json()) == 2
