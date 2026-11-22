"""On-demand Tuya Smart Control cloud snapshots for the selected delivery camera."""

import ipaddress
import json
import time
from io import BytesIO
from urllib.parse import urlsplit

import httpx
from PIL import Image, UnidentifiedImageError


class TuyaCaptureError(RuntimeError):
    """A camera or cloud failure that is safe to show without credentials or signed URLs."""


MAX_JPEG_BYTES = 8 * 1024 * 1024
MAX_IMAGE_PIXELS = 20_000_000


class TuyaCapture:
    def __init__(self, api_key: str, endpoint: str, device_id: str):
        self.api_key = api_key
        self.endpoint = endpoint.rstrip("/")
        self.device_id = device_id

    def capture_jpeg(self) -> bytes:
        """Allocate one snapshot, resolve its temporary URL, and download a valid JPEG."""
        path = f"/v1.0/end-user/ipc/{self.device_id}/capture"
        with httpx.Client(
            timeout=httpx.Timeout(10.0, connect=5.0),
            follow_redirects=False,
            headers={"Authorization": f"Bearer {self.api_key}"},
        ) as client:
            allocated = self._post(
                client,
                f"{path}/allocate",
                {
                    "capture_json": json.dumps(
                        {"device_id": self.device_id, "capture_type": "PIC", "pic_count": 1}
                    )
                },
            )
            bucket = allocated.get("bucket")
            image_key = allocated.get("image_object_key")
            if not isinstance(bucket, str) or not isinstance(image_key, str):
                raise TuyaCaptureError("Tuya did not allocate an image slot")

            resolve = {
                "device_id": self.device_id,
                "capture_type": "PIC",
                "bucket": bucket,
                "image_object_key": image_key,
                "user_privacy_consent_accepted": True,
            }
            if allocated.get("encryption_key"):
                resolve["encryption_key"] = allocated["encryption_key"]

            deadline = time.monotonic() + 35
            while time.monotonic() < deadline:
                time.sleep(2)
                result = self._post(
                    client, f"{path}/resolve", {"resolve_json": json.dumps(resolve)}
                )
                image_url = result.get("decrypt_image_url")
                # The Singapore endpoint can return a usable URL with status=ACCEPTED.
                if isinstance(image_url, str) and image_url:
                    return self._download_jpeg(image_url)
                if result.get("status") in {"FAILED", "ERROR", "UNSUPPORTED"}:
                    raise TuyaCaptureError("Tuya could not capture a camera image")
            raise TuyaCaptureError("Tuya snapshot was not ready within 35 seconds")

    def _post(self, client: httpx.Client, path: str, payload: dict[str, str]) -> dict:
        try:
            response = client.post(f"{self.endpoint}{path}", json=payload)
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise TuyaCaptureError("Tuya snapshot request failed") from exc
        if not isinstance(data, dict) or data.get("success") is not True:
            raise TuyaCaptureError("Tuya rejected the snapshot request")
        result = data.get("result")
        if not isinstance(result, dict):
            raise TuyaCaptureError("Tuya returned an invalid snapshot response")
        return result

    def _download_jpeg(self, image_url: str) -> bytes:
        parsed = urlsplit(image_url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise TuyaCaptureError("Tuya returned an unsafe image URL")
        try:
            address = ipaddress.ip_address(parsed.hostname)
        except ValueError:
            if parsed.hostname == "localhost" or parsed.hostname.endswith(".localhost"):
                raise TuyaCaptureError("Tuya returned an unsafe image URL") from None
        else:
            if not address.is_global:
                raise TuyaCaptureError("Tuya returned an unsafe image URL")

        try:
            # Signed media URLs must never receive the Tuya bearer key.
            with httpx.Client(timeout=15.0, follow_redirects=False) as media_client:
                with media_client.stream("GET", image_url) as response:
                    response.raise_for_status()
                    content = bytearray()
                    for chunk in response.iter_bytes():
                        content.extend(chunk)
                        if len(content) > MAX_JPEG_BYTES:
                            raise TuyaCaptureError("Tuya image exceeds the size limit")
        except httpx.HTTPError as exc:
            raise TuyaCaptureError("Tuya image download failed") from exc

        try:
            with Image.open(BytesIO(content)) as image:
                if image.format != "JPEG" or image.width * image.height > MAX_IMAGE_PIXELS:
                    raise TuyaCaptureError("Tuya returned an invalid JPEG")
                image.load()
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            raise TuyaCaptureError("Tuya returned an invalid JPEG") from exc
        if not content.startswith(b"\xff\xd8") or not content.endswith(b"\xff\xd9"):
            raise TuyaCaptureError("Tuya returned an incomplete JPEG")
        return bytes(content)
