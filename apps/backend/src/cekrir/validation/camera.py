from fastapi import HTTPException, Request

from cekrir.services.barcodes import MAX_FRAME_BYTES


async def jpeg_frame(request: Request) -> bytes:
    if request.headers.get("content-type", "").split(";")[0].lower() != "image/jpeg":
        raise HTTPException(status_code=415, detail="Content-Type must be image/jpeg")
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            size = int(content_length)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid Content-Length") from exc
        if size > MAX_FRAME_BYTES:
            raise HTTPException(status_code=413, detail="JPEG frame exceeds 512 KiB")
    frame = bytearray()
    async for chunk in request.stream():
        if len(frame) + len(chunk) > MAX_FRAME_BYTES:
            raise HTTPException(status_code=413, detail="JPEG frame exceeds 512 KiB")
        frame.extend(chunk)
    return bytes(frame)
