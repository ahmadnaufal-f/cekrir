from io import BytesIO

from fastapi import HTTPException, Request
from PIL import Image
from starlette.concurrency import run_in_threadpool

SCREENSHOT_FORMATS = {"image/png": "PNG", "image/jpeg": "JPEG", "image/webp": "WEBP"}
MAX_SCREENSHOT_BYTES = 5 * 1024 * 1024
MAX_SCREENSHOT_PIXELS = 20_000_000


def validate_image(data: bytes, image_format: str) -> None:
    try:
        with Image.open(BytesIO(data), formats=[image_format]) as image:
            if image.width * image.height > MAX_SCREENSHOT_PIXELS:
                raise HTTPException(422, "Screenshot exceeds 20 megapixels")
            if getattr(image, "is_animated", False):
                raise HTTPException(422, "Screenshot must be a static image")
            image.load()
    except (OSError, ValueError, SyntaxError, Image.DecompressionBombError) as exc:
        raise HTTPException(422, "Invalid screenshot image") from exc


async def read_screenshot(request: Request) -> tuple[bytes, str]:
    media_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    image_format = SCREENSHOT_FORMATS.get(media_type)
    if image_format is None:
        raise HTTPException(415, "Screenshot must be PNG, JPEG, or WebP")

    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            size = int(content_length)
        except ValueError as exc:
            raise HTTPException(400, "Invalid Content-Length") from exc
        if size > MAX_SCREENSHOT_BYTES:
            raise HTTPException(413, "Screenshot exceeds 5 MiB")

    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > MAX_SCREENSHOT_BYTES:
            raise HTTPException(413, "Screenshot exceeds 5 MiB")
        body.extend(chunk)

    data = bytes(body)
    await run_in_threadpool(validate_image, data, image_format)
    return data, media_type
