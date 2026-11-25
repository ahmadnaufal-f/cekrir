import pytest
from fastapi.testclient import TestClient

from cekrir.config import Settings
from cekrir.main import create_app


@pytest.mark.parametrize(
    "origin",
    [
        "https://cekrir.arkaes.dev",
        "capacitor://localhost",
        "http://localhost",
        "https://localhost",
    ],
)
def test_frontend_origins_can_make_authorized_requests(origin, monkeypatch):
    monkeypatch.delenv("CEKRIR_CORS_ORIGINS", raising=False)
    client = TestClient(create_app(settings=Settings(_env_file=None)))

    response = client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    assert response.headers["access-control-allow-credentials"] == "true"
    actual = client.get("/health", headers={"Origin": origin})
    assert actual.headers["access-control-allow-origin"] == origin
    assert actual.headers["access-control-allow-credentials"] == "true"


def test_untrusted_origin_is_not_allowed(monkeypatch):
    monkeypatch.delenv("CEKRIR_CORS_ORIGINS", raising=False)
    client = TestClient(create_app(settings=Settings(_env_file=None)))
    response = client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": "https://untrusted.example",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers
