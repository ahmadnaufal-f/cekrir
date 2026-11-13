from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool

from cekrir.api.dependencies import get_provider, get_repository, require_ingest_key
from cekrir.repository import ShipmentRepository
from cekrir.schemas import CameraFrameInput, CameraFrameResult, DetectionInput, FrameDetection
from cekrir.services.barcodes import MAX_FRAME_BYTES, InvalidCameraFrame, decode_frame
from cekrir.services.shipments import register_shipment
from cekrir.services.tracking import TrackingProvider

router = APIRouter(prefix="/api/v1/detections", tags=["detections"])


@router.post(
    "/frame",
    response_model=CameraFrameResult,
    dependencies=[Depends(require_ingest_key)],
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {"image/jpeg": {"schema": {"type": "string", "format": "binary"}}},
        }
    },
)
async def ingest_camera_frame(
    request: Request,
    metadata: Annotated[CameraFrameInput, Query()],
    repository: ShipmentRepository = Depends(get_repository),
    provider: TrackingProvider = Depends(get_provider),
):
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
    try:
        codes = await run_in_threadpool(decode_frame, bytes(frame))
    except InvalidCameraFrame as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    candidates: dict[str, DetectionInput] = {}
    for code in codes:
        try:
            payload = DetectionInput(resi_number=code, **metadata.model_dump())
        except ValidationError:
            continue
        candidates[payload.resi_number] = payload
    if len(candidates) != 1:
        # Shipping labels may contain several unrelated codes. Never guess
        # between multiple valid-looking candidates in a single frame.
        return CameraFrameResult(ambiguous=len(candidates) > 1)

    payload = next(iter(candidates.values()))
    shipment, created = await run_in_threadpool(register_shipment, repository, payload, provider)
    return CameraFrameResult(
        detected_count=1,
        detections=[
            FrameDetection(
                resi_number=shipment.resi_number, shipment_id=shipment.id, created=created
            )
        ],
    )
