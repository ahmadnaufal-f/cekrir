import subprocess
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from cekrir.cctv_capture import CaptureError, capture_jpeg
from cekrir.cctv_poc_app import app


def test_capture_uses_tcp_and_encodes_credentials():
    jpeg = b"\xff\xd8example\xff\xd9"
    with patch("cekrir.cctv_capture.subprocess.run") as run:
        run.return_value = subprocess.CompletedProcess([], 0, jpeg, b"")
        assert (
            capture_jpeg("rtsp://192.168.18.23:8554/Streaming/Channels/101", "admin", "a@b:c")
            == jpeg
        )
    command = run.call_args.args[0]
    assert command[command.index("-rtsp_transport") + 1] == "tcp"
    assert command[command.index("-timeout") + 1] == "10000000"
    assert command[command.index("-i") + 1] == (
        "rtsp://admin:a%40b%3Ac@192.168.18.23:8554/Streaming/Channels/101"
    )
    assert run.call_args.kwargs["timeout"] == 15


def test_capture_rejects_missing_configuration_without_starting_ffmpeg():
    with patch("cekrir.cctv_capture.subprocess.run") as run:
        with pytest.raises(CaptureError):
            capture_jpeg("", "admin", "password")
        run.assert_not_called()


def test_capture_failure_does_not_expose_credentials():
    with patch("cekrir.cctv_capture.subprocess.run") as run:
        run.return_value = subprocess.CompletedProcess([], 1, b"", b"secret password and URL")
        with pytest.raises(CaptureError) as error:
            capture_jpeg("rtsp://192.168.18.23:8554/stream", "admin", "secret")
    assert "secret" not in str(error.value)


def test_snapshot_endpoint_returns_jpeg(monkeypatch):
    monkeypatch.setenv("CEKRIR_CCTV_RTSP_URL", "rtsp://192.168.18.23:8554/stream")
    monkeypatch.setenv("CEKRIR_CCTV_USERNAME", "admin")
    monkeypatch.setenv("CEKRIR_CCTV_PASSWORD", "password")
    with patch(
        "cekrir.cctv_poc_app.capture_jpeg", return_value=b"\xff\xd8frame\xff\xd9"
    ) as capture:
        response = TestClient(app).post("/snapshot")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    assert response.headers["cache-control"] == "no-store"
    assert response.content == b"\xff\xd8frame\xff\xd9"
    capture.assert_called_once_with("rtsp://192.168.18.23:8554/stream", "admin", "password")
