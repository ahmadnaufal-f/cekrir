from io import BytesIO

import httpx
import pytest
from PIL import Image

from cekrir.services import tuya_capture


def jpeg() -> bytes:
    output = BytesIO()
    Image.new("RGB", (80, 60), color="green").save(output, format="JPEG")
    return output.getvalue()


def test_tuya_capture_accepts_url_before_ready_and_keeps_key_off_media_request(monkeypatch):
    calls = []
    content = jpeg()

    def respond(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if request.url.path.endswith("/allocate"):
            return httpx.Response(
                200,
                json={
                    "success": True,
                    "result": {
                        "status": "ACCEPTED",
                        "bucket": "bucket",
                        "image_object_key": "image-key",
                        "encryption_key": "encryption-key",
                    },
                },
            )
        if request.url.path.endswith("/resolve"):
            return httpx.Response(
                200,
                json={
                    "success": True,
                    "result": {
                        "status": "ACCEPTED",
                        "decrypt_image_url": "https://media.example.test/image?signature=secret",
                    },
                },
            )
        assert request.url.host == "media.example.test"
        return httpx.Response(200, content=content, headers={"Content-Type": "image/jpeg"})

    original_client = httpx.Client
    transport = httpx.MockTransport(respond)
    monkeypatch.setattr(
        tuya_capture.httpx,
        "Client",
        lambda **kwargs: original_client(transport=transport, **kwargs),
    )
    monkeypatch.setattr(tuya_capture.time, "sleep", lambda _: None)

    capture = tuya_capture.TuyaCapture("sk-test", "https://api.example.test", "camera-123")
    assert capture.capture_jpeg() == content
    assert len(calls) == 3
    assert all(call.headers.get("authorization") == "Bearer sk-test" for call in calls[:2])
    assert "authorization" not in calls[2].headers


def test_tuya_capture_rejects_non_jpeg_media(monkeypatch):
    def respond(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/allocate"):
            return httpx.Response(
                200, json={"success": True, "result": {"bucket": "a", "image_object_key": "b"}}
            )
        if request.url.path.endswith("/resolve"):
            return httpx.Response(
                200,
                json={"success": True, "result": {"decrypt_image_url": "https://media.test/img"}},
            )
        return httpx.Response(200, content=b"not a jpeg")

    original_client = httpx.Client
    monkeypatch.setattr(
        tuya_capture.httpx,
        "Client",
        lambda **kwargs: original_client(transport=httpx.MockTransport(respond), **kwargs),
    )
    monkeypatch.setattr(tuya_capture.time, "sleep", lambda _: None)
    with pytest.raises(tuya_capture.TuyaCaptureError, match="invalid JPEG"):
        tuya_capture.TuyaCapture("sk-test", "https://api.test", "camera-123").capture_jpeg()
