import base64
import json
from io import BytesIO
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from cekrir.config import Settings
from cekrir.db.session import get_session
from cekrir.main import create_app
from cekrir.services import screenshot_analysis
from cekrir.validation import screenshots

ROUTE = "/api/v1/shipments/analyze-screenshot"
PNG = {"Content-Type": "image/png"}
EMPTY = {"resi_number": None, "courier_service": None, "sender_name": None, "product_names": []}


def image_bytes(image_format="PNG", *, animated=False):
    buffer = BytesIO()
    first = Image.new("RGB", (16, 12), "white")
    if animated:
        second = Image.new("RGB", first.size, "black")
        first.save(buffer, image_format, save_all=True, append_images=[second], duration=100)
    else:
        first.save(buffer, image_format)
    return buffer.getvalue()


@pytest.fixture
def analyzer(monkeypatch):
    app = create_app(Settings(_env_file=None, openai_api_key="test-token"))

    def no_shipment_session():
        pytest.fail("Screenshot analysis should not open a shipment session")

    def authenticate(token, _settings, _session_factory):
        if token in {"admin", "member"}:
            return {"permissions": {"shipments:create"}}
        if token == "read-only":
            return {"permissions": {"shipments:read"}}
        return None

    app.dependency_overrides[get_session] = no_shipment_session
    monkeypatch.setattr("cekrir.middleware.role_permissions.authenticate_token", authenticate)
    return TestClient(app, headers={"Authorization": "Bearer member"})


def stub_provider(monkeypatch, handler):
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(screenshot_analysis.httpx, "AsyncClient", lambda **_kwargs: client)


def provider_result(value):
    return httpx.Response(
        200,
        json={
            "status": "completed",
            "output": [
                {"type": "reasoning"},
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": json.dumps(value)}],
                },
            ],
        },
    )


@pytest.mark.parametrize("role", ["admin", "member"])
def test_returns_only_review_fields_with_original_image_and_exact_resi(analyzer, monkeypatch, role):
    screenshot = image_bytes()
    extracted = {
        "resi_number": "000xY-128",
        "courier_service": "SPX Express",
        "sender_name": None,
        "product_names": ["Storage box", "Desk mat"],
    }

    def provider(request):
        assert request.url == screenshot_analysis.OPENAI_RESPONSES_URL
        assert request.headers["Authorization"] == "Bearer test-token"
        payload = json.loads(request.content)
        assert payload["model"] == "gpt-6-luna" and payload["store"] is False
        schema = payload["text"]["format"]
        assert schema["strict"] is True and schema["schema"]["additionalProperties"] is False
        assert set(schema["schema"]["properties"]) == set(extracted)
        data_url = payload["input"][0]["content"][0]["image_url"]
        header, image = data_url.split(",", 1)
        assert header == "data:image/png;base64"
        assert base64.b64decode(image) == screenshot
        return provider_result(extracted)

    stub_provider(monkeypatch, provider)
    response = analyzer.post(
        ROUTE, content=screenshot, headers={**PNG, "Authorization": f"Bearer {role}"}
    )
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "private, no-store"
    assert response.json() == extracted


def test_authorizes_before_reading_upload(analyzer, monkeypatch):
    analyze = AsyncMock()
    monkeypatch.setattr(screenshot_analysis, "analyze", analyze)
    for token, status in [("", 401), ("read-only", 403)]:
        response = analyzer.post(ROUTE, headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == status
    analyze.assert_not_called()


@pytest.mark.parametrize(
    "image_format,media_type", [("JPEG", "image/jpeg"), ("WEBP", "image/webp")]
)
def test_accepts_formats_and_returns_blank_ambiguous_result(
    analyzer, monkeypatch, image_format, media_type
):
    stub_provider(monkeypatch, lambda _request: provider_result(EMPTY))
    response = analyzer.post(
        ROUTE, content=image_bytes(image_format), headers={"Content-Type": media_type}
    )
    assert response.status_code == 200
    assert response.json() == EMPTY


def test_rejects_invalid_and_oversized_uploads_before_provider(analyzer, monkeypatch):
    analyze = AsyncMock()
    monkeypatch.setattr(screenshot_analysis, "analyze", analyze)
    assert analyzer.post(ROUTE, content=b"", headers=PNG).status_code == 422
    assert analyzer.post(ROUTE, content=b"bad image", headers=PNG).status_code == 422
    assert analyzer.post(ROUTE, content=image_bytes("JPEG"), headers=PNG).status_code == 422
    assert analyzer.post(ROUTE, content=image_bytes(), headers={}).status_code == 415
    assert analyzer.post(ROUTE, content=image_bytes(animated=True), headers=PNG).status_code == 422
    monkeypatch.setattr(screenshots, "MAX_SCREENSHOT_PIXELS", 100)
    assert analyzer.post(ROUTE, content=image_bytes(), headers=PNG).status_code == 422
    monkeypatch.setattr(screenshots, "MAX_SCREENSHOT_BYTES", 5)
    for body in (b"123456", iter([b"123", b"456"])):
        assert analyzer.post(ROUTE, content=body, headers=PNG).status_code == 413
    analyze.assert_not_called()


@pytest.mark.parametrize(
    "failure,status", [("extra field", 502), (429, 503), (504, 504), ("timeout", 504)]
)
def test_provider_failures_return_generic_errors(analyzer, monkeypatch, failure, status):
    def provider(request):
        if failure == "timeout":
            raise httpx.ReadTimeout("private provider detail", request=request)
        if isinstance(failure, int):
            return httpx.Response(failure, json={"error": "private provider detail"})
        return provider_result({**EMPTY, "recipient_name": "private provider detail"})

    stub_provider(monkeypatch, provider)
    response = analyzer.post(ROUTE, content=image_bytes(), headers=PNG)
    assert response.status_code == status
    assert "private provider detail" not in response.text


def test_unconfigured_provider_leaves_manual_review_available(analyzer):
    analyzer.app.state.settings.openai_api_key = None
    response = analyzer.post(ROUTE, content=image_bytes(), headers=PNG)
    assert response.status_code == 503
