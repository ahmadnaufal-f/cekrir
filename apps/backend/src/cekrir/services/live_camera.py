import asyncio
from collections.abc import AsyncIterator
from io import BytesIO
from threading import Lock

from PIL import Image, UnidentifiedImageError

from cekrir.services.barcodes import MAX_FRAME_DIMENSION, MAX_FRAME_PIXELS


class InvalidLiveFrame(ValueError):
    pass


class LatestFrame:
    def __init__(self):
        self._frame: bytes | None = None
        self._revision = 0
        self._lock = Lock()

    def save(self, frame: bytes) -> None:
        try:
            with Image.open(BytesIO(frame)) as image:
                width, height = image.size
                if (
                    image.format != "JPEG"
                    or max(width, height) > MAX_FRAME_DIMENSION
                    or width * height > MAX_FRAME_PIXELS
                ):
                    raise InvalidLiveFrame("Expected a JPEG up to 2 megapixels")
                image.verify()
        except (UnidentifiedImageError, Image.DecompressionBombError, OSError) as exc:
            raise InvalidLiveFrame("Invalid JPEG image") from exc
        with self._lock:
            self._frame = frame
            self._revision += 1

    def get(self) -> bytes | None:
        with self._lock:
            return self._frame

    async def stream(self) -> AsyncIterator[bytes]:
        last_revision = 0
        while True:
            with self._lock:
                frame, revision = self._frame, self._revision
            if frame is not None and revision != last_revision:
                last_revision = revision
                yield (
                    b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: "
                    + str(len(frame)).encode("ascii")
                    + b"\r\n\r\n"
                    + frame
                    + b"\r\n"
                )
            await asyncio.sleep(0.05)
