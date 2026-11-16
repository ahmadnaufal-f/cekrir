from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import ValidationError
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from cekrir.db.session import get_session
from cekrir.routers.shipments import get_provider, get_publisher
from cekrir.schemas import (
    CameraFrameInput,
    CameraFrameResult,
    DetectionInput,
    DetectionResult,
    FrameDetection,
)
from cekrir.services.barcodes import MAX_FRAME_BYTES, InvalidCameraFrame, decode_frame
from cekrir.services.notifications import NotificationPublisher
from cekrir.services.shipments import register_shipment
from cekrir.services.tracking import TrackingProvider

router = APIRouter(prefix="/api/v1", tags=["detections"])
camera_router = APIRouter(prefix="/api/v1/detections", tags=["detections"])


@router.post("/detections", response_model=DetectionResult)
def ingest_detection(
    payload: DetectionInput,
    session: Session = Depends(get_session),
    provider: TrackingProvider = Depends(get_provider),
    publisher: NotificationPublisher = Depends(get_publisher),
):
    shipment, created, notification = register_shipment(session, payload, provider)
    if notification:
        publisher.publish(notification)
    return DetectionResult(created=created, shipment=shipment)


@camera_router.post(
    "/frame",
    response_model=CameraFrameResult,
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
    session: Session = Depends(get_session),
    provider: TrackingProvider = Depends(get_provider),
    publisher: NotificationPublisher = Depends(get_publisher),
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
        return CameraFrameResult(ambiguous=len(candidates) > 1)

    payload = next(iter(candidates.values()))
    shipment, created, notification = await run_in_threadpool(
        register_shipment, session, payload, provider
    )
    if notification:
        await run_in_threadpool(publisher.publish, notification)
    return CameraFrameResult(
        detected_count=1,
        detections=[
            FrameDetection(
                resi_number=shipment.resi_number, shipment_id=shipment.id, created=created
            )
        ],
    )
