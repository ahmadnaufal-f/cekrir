import hmac
import logging
from hashlib import sha256
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient

from cekrir.config import Settings
from cekrir.main import create_app
from cekrir.middleware.role_permissions import TUYA_OAUTH_CALLBACK_PATH
from cekrir.routers import tuya_oauth

START_PATH = "/api/v1/integrations/tuya/oauth/start/sg"
APP_ID = "pilot-app-id"
APP_SECRET = "pilot-app-secret"
FINGERPRINT = "AB:" * 19 + "CD"
HOST = "https://api.example.test"
CALLBACK_URL = f"{HOST}{TUYA_OAUTH_CALLBACK_PATH}"
H5_URL = httpx.URL(
    "https://tuya.example.test/d/login", params={"client_id": APP_ID, "redirect_uri": CALLBACK_URL}
)
ADMIN_AUTH = {"Authorization": "Bearer pilot-admin"}


@pytest.fixture
def pilot(monkeypatch):
    state = {}
    upstream_requests = []
    upstream_reply = {"success": True, "result": {"access_token": "private-tuya-token"}}
    app = create_app(
        Settings(
            _env_file=None,
            tuya_oauth_client_id=APP_ID,
            tuya_oauth_client_secret=APP_SECRET,
            tuya_oauth_android_sha1=FINGERPRINT,
            tuya_oauth_h5_url=str(H5_URL),
        )
    )

    def save(key, value, *, ex, nx):
        assert ex == 600 and nx is True
        assert key not in state
        state[key] = value
        return True

    def upstream(request):
        upstream_requests.append(request)
        return httpx.Response(200, json=upstream_reply)

    def authenticate(token, *_):
        return {"permissions": ["locations:manage"] if token == "pilot-admin" else []}

    monkeypatch.setattr(app.state.redis.client, "set", save)
    monkeypatch.setattr(app.state.redis.client, "getdel", lambda key: state.pop(key, None))
    monkeypatch.setattr("cekrir.middleware.role_permissions.authenticate_token", authenticate)
    monkeypatch.setattr(
        tuya_oauth,
        "httpx",
        SimpleNamespace(
            URL=httpx.URL,
            Client=lambda **options: httpx.Client(
                **options, transport=httpx.MockTransport(upstream)
            ),
        ),
    )
    client = TestClient(app, base_url=HOST)
    try:
        yield client, upstream_requests, upstream_reply
    finally:
        client.close()
        app.state.redis.client.close()
        app.state.engine.dispose()


def test_singapore_callback_exchanges_code_once(pilot, caplog):
    client, requests, _ = pilot
    assert client.post(START_PATH).status_code == 401
    assert client.post(START_PATH, headers={"Authorization": "Bearer member"}).status_code == 403
    start = client.post(START_PATH, headers=ADMIN_AUTH)
    assert start.status_code == 200
    assert start.headers["cache-control"] == "no-store"
    login_url = httpx.URL(start.json()["authorization_url"])
    assert login_url.copy_remove_param("state") == H5_URL
    state = login_url.params["state"]
    params = {"code": "private+code", "state": state}

    with caplog.at_level(logging.INFO):
        response = client.get(TUYA_OAUTH_CALLBACK_PATH, params=params)
        logging.getLogger("uvicorn.access").info(
            '%s - "%s %s HTTP/%s" %d',
            "127.0.0.1",
            "GET",
            f"{TUYA_OAUTH_CALLBACK_PATH}?code=private-code",
            "1.1",
            200,
        )

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.json() == {"detail": "Tuya authorization succeeded. You can close this page."}
    assert "private-code" not in caplog.text
    assert "grant_type=2" not in caplog.text
    assert client.get(TUYA_OAUTH_CALLBACK_PATH, params=params).status_code == 400
    assert client.post(TUYA_OAUTH_CALLBACK_PATH, params=params).status_code == 401

    (request,) = requests
    url = "https://openapi-sg.iotbing.com/v1.0/token?code=private%2Bcode&grant_type=2"
    assert str(request.url) == url
    assert request.method == "GET"
    assert request.headers["client_id"] == APP_ID
    assert request.headers["sign_method"] == "HMAC-SHA256"
    signed = (
        f"{APP_ID}{request.headers['t']}{request.headers['nonce']}{FINGERPRINT}id.cekrir.app"
        f"GET\n{sha256(b'').hexdigest()}\n\n{request.url.raw_path.decode()}"
    )
    assert (
        request.headers["sign"]
        == hmac.digest(APP_SECRET.encode(), signed.encode(), "sha256").hex().upper()
    )


def test_callback_requires_a_pending_state_and_hides_tuya_error_details(pilot):
    client, requests, upstream_reply = pilot
    assert client.get(TUYA_OAUTH_CALLBACK_PATH, params={"code": "code"}).status_code == 400
    assert (
        client.get(TUYA_OAUTH_CALLBACK_PATH, params={"code": "code", "state": "a" * 43}).status_code
        == 400
    )
    assert requests == []

    start = client.post(START_PATH, headers=ADMIN_AUTH)
    state = httpx.URL(start.json()["authorization_url"]).params["state"]
    upstream_reply.update(success=False, code=1106, msg="password or credential details")
    response = client.get(TUYA_OAUTH_CALLBACK_PATH, params={"code": "code", "state": state})
    assert response.status_code == 502
    assert response.json() == {
        "detail": "Tuya returned an error during OAuth code exchange (code 1106)."
    }
