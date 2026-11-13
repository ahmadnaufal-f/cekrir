from unittest.mock import patch

import httpx
import pytest
from pydantic import ValidationError

from cekrir.config import Settings
from cekrir.services.tracking import HttpTrackingProvider, TrackingUnavailable


def test_http_provider_uses_configured_gateway_and_normalizes_response():
    provider = HttpTrackingProvider(
        Settings(
            _env_file=None,
            tracking_provider="http",
            tracking_api_url="https://tracking.example/track",
            tracking_api_key="secret",
        )
    )
    response = httpx.Response(
        200,
        json={"status": "delivered", "summary": "Delivered to recipient", "history": []},
        request=httpx.Request("POST", "https://tracking.example/track"),
    )
    with patch("cekrir.services.tracking.httpx.post", return_value=response) as post:
        assert provider.lookup("AB12345", "jne").status == "delivered"
        assert post.call_args.kwargs["json"] == {"resi_number": "AB12345", "courier": "jne"}
        assert post.call_args.kwargs["headers"] == {"Authorization": "Bearer secret"}
        assert post.call_args.kwargs["follow_redirects"] is False


@pytest.mark.parametrize("status,body", [(429, {}), (200, {"status": "unknown"}), (500, {})])
def test_http_failures_are_sanitized(status, body):
    settings = Settings(_env_file=None, tracking_provider="http", tracking_api_url="https://x.test")
    response = httpx.Response(
        status, json=body, request=httpx.Request("POST", "https://x.test?key=secret")
    )
    with patch("cekrir.services.tracking.httpx.post", return_value=response):
        with pytest.raises(TrackingUnavailable, match="temporarily unavailable"):
            HttpTrackingProvider(settings).lookup("AB12345", "jne")


def test_http_provider_requires_url():
    with pytest.raises(ValidationError, match="CEKRIR_TRACKING_API_URL"):
        Settings(_env_file=None, tracking_provider="http")
