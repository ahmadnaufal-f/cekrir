"""One-shot RTSP capture for the local CCTV proof of concept."""

import subprocess
from urllib.parse import quote, urlsplit, urlunsplit


class CaptureError(RuntimeError):
    pass


def capture_jpeg(rtsp_url: str, username: str, password: str) -> bytes:
    """Connect over RTSP/TCP and return one JPEG without logging credentials."""
    try:
        parsed = urlsplit(rtsp_url)
        if parsed.scheme != "rtsp" or not parsed.hostname or "@" in parsed.netloc:
            raise ValueError
        if not username or not password:
            raise ValueError
        netloc = f"{quote(username, safe='')}:{quote(password, safe='')}@{parsed.netloc}"
        source = urlunsplit(parsed._replace(netloc=netloc))
    except ValueError as exc:
        raise CaptureError("Set an RTSP URL and separate ONVIF username/password") from exc

    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-nostdin",
        "-rtsp_transport",
        "tcp",
        "-timeout",
        "10000000",
        "-i",
        source,
        "-frames:v",
        "1",
        "-f",
        "image2pipe",
        "-vcodec",
        "mjpeg",
        "pipe:1",
    ]
    try:
        result = subprocess.run(command, capture_output=True, timeout=15, check=False)
    except FileNotFoundError as exc:
        raise CaptureError("FFmpeg is not installed") from exc
    except subprocess.TimeoutExpired as exc:
        raise CaptureError("CCTV capture timed out after 15 seconds") from exc
    if (
        result.returncode != 0
        or not result.stdout.startswith(b"\xff\xd8")
        or not result.stdout.endswith(b"\xff\xd9")
    ):
        # FFmpeg stderr may include the credential-bearing RTSP URL.
        raise CaptureError("CCTV capture failed; check LAN access, credentials, and stream URL")
    return result.stdout
