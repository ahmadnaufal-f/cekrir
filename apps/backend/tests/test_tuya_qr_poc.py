import hmac
from hashlib import sha256

import httpx
import pytest
from fastapi.testclient import TestClient

from cekrir.tuya_qr_poc import TuyaProject, app, project_client

ORIGIN = "http://127.0.0.1:8003"
LINK = {"uid": "pilot-uid", "device_id": "pilot-camera"}
ACCESS_ID = "test-project-id"
ACCESS_SECRET = "test-project-secret"
ACCESS_TOKEN = "test-token"


@pytest.fixture
def pilot():
    requests = []
    devices = []
    upstream_errors = {}

    def upstream(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        signed_path = request.url.raw_path.decode()
        signed_data = "\n".join(
            (request.method, sha256(request.content).hexdigest(), "", signed_path)
        )
        prefix = "".join(
            request.headers.get(field, "") for field in ("client_id", "access_token", "t", "nonce")
        )
        assert request.headers["client_id"] == ACCESS_ID
        assert request.headers["sign_method"] == "HMAC-SHA256"
        expected = hmac.digest(ACCESS_SECRET.encode(), (prefix + signed_data).encode(), "sha256")
        assert request.headers["sign"] == expected.hex().upper()

        if signed_path == "/v1.0/token?grant_type=1":
            assert "access_token" not in request.headers
            result = {"access_token": ACCESS_TOKEN}
        else:
            assert request.headers["access_token"] == ACCESS_TOKEN
            if request.url.path == "/v1.0/users/pilot-uid/devices":
                assert request.url.params["from"] == "home"
                result = devices
            else:
                assert request.url.path == "/v1.0/cameras/pilot-camera/actions/capture"
                assert request.method == "POST"
                result = {"sn": "capture-42"}
        if request.url.path in upstream_errors:
            return httpx.Response(200, json=upstream_errors[request.url.path])
        return httpx.Response(200, json={"success": True, "result": result})

    with httpx.Client(
        base_url="https://openapi-sg.iotbing.com", transport=httpx.MockTransport(upstream)
    ) as cloud:
        app.dependency_overrides[project_client] = lambda: TuyaProject(
            cloud, ACCESS_ID, ACCESS_SECRET
        )
        try:
            with TestClient(app, base_url=ORIGIN, client=("127.0.0.1", 12345)) as client:
                yield client, devices, requests, upstream_errors
        finally:
            app.dependency_overrides.clear()


def test_verifies_a_visible_camera_and_requests_capture_after_rechecking(pilot):
    client, devices, requests, _ = pilot
    headers = {"Origin": ORIGIN}
    assert client.post("/api/verify", json=LINK, headers=headers).status_code == 404

    devices.extend(
        [
            {"id": "other-device", "name": "Private light"},
            {"id": "pilot-camera", "name": "Front door", "online": True, "local_key": "private"},
        ]
    )
    assert client.post("/api/verify", json=LINK, headers=headers).json() == {
        "name": "Front door",
        "online": True,
    }
    accepted = client.post("/api/capture", json=LINK, headers=headers)
    assert accepted.json() == {"command_id": "capture-42"}

    devices.clear()
    assert client.post("/api/capture", json=LINK, headers=headers).status_code == 404
    assert len([request for request in requests if request.method == "POST"]) == 1


def test_local_poc_rejects_cross_origin_requests_and_invalid_ids(pilot):
    client, _, requests, _ = pilot
    assert client.get("/").status_code == 200
    assert (
        client.post("/api/verify", json=LINK, headers={"Origin": "https://other.test"}).status_code
        == 403
    )
    invalid = {**LINK, "device_id": "../../another-device"}
    assert client.post("/api/capture", json=invalid, headers={"Origin": ORIGIN}).status_code == 422
    assert requests == []


@pytest.mark.parametrize(
    ("path", "operation", "request_id", "with_request_id"),
    [
        ("/v1.0/token", "project authentication", None, False),
        ("/v1.0/users/pilot-uid/devices", "linked account device lookup", ACCESS_TOKEN, False),
        (
            "/v1.0/cameras/pilot-camera/actions/capture",
            "snapshot capture",
            "c5224fa6b7d840e18c13f3d991d02241",
            True,
        ),
    ],
)
def test_capture_errors_identify_failed_operation(
    pilot, path, operation, request_id, with_request_id
):
    client, devices, _, upstream_errors = pilot
    devices.append({"id": LINK["device_id"], "online": True})
    upstream_errors[path] = {"success": False, "code": 500, "tid": request_id, "msg": ACCESS_SECRET}

    response = client.post("/api/capture", json=LINK, headers={"Origin": ORIGIN})

    assert response.status_code == 502
    detail = f"Tuya returned an error during {operation} (code 500)."
    if with_request_id:
        detail += f" Tuya request ID {request_id}."
    assert response.json() == {"detail": detail}
