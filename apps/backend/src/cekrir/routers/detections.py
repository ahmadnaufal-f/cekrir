from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from cekrir.db.session import get_session
from cekrir.dependencies import get_provider, get_publisher
from cekrir.middleware import RequirePermission
from cekrir.schemas import CameraFrameResult, DetectionResult
from cekrir.services import detections
from cekrir.services.barcodes import InvalidCameraFrame
from cekrir.services.cctv_photos import schedule_photo
from cekrir.services.notifications import NotificationPublisher
from cekrir.services.tracking import TrackingProvider
from cekrir.validation.camera import jpeg_frame
from cekrir.validation.device_auth import verified_esp
from cekrir.validation.shipments import CameraFrameInput, CourierInput, DetectionInput

router = APIRouter(prefix="/api/v1", tags=["detections"])
camera_router = APIRouter(prefix="/api/v1/detections", tags=["detections"])
device_router = APIRouter(prefix="/api/v1/devices", tags=["devices"])


@device_router.post(
    "/{device_id}/frames",
    response_model=CameraFrameResult,
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {"image/jpeg": {"schema": {"type": "string", "format": "binary"}}},
        }
    },
)
async def ingest_device_frame(
    metadata: Annotated[CourierInput, Query()],
    request: Request,
    background_tasks: BackgroundTasks,
    device_id: str = Depends(verified_esp),
    frame: bytes = Depends(jpeg_frame),
    session: Session = Depends(get_session),
    provider: TrackingProvider = Depends(get_provider),
    publisher: NotificationPublisher = Depends(get_publisher),
):
    try:
        result = await run_in_threadpool(
            detections.ingest_esp_frame, frame, device_id, metadata, session, provider, publisher
        )
        for detection in result.detections:
            schedule_photo(session, detection.shipment_id, request, background_tasks)
        return result
    except InvalidCameraFrame as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post(
    "/detections",
    response_model=DetectionResult,
    dependencies=[Depends(RequirePermission("detections:create", allow_ingest_key=True))],
)
def ingest_detection(
    payload: DetectionInput,
    request: Request,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
    provider: TrackingProvider = Depends(get_provider),
    publisher: NotificationPublisher = Depends(get_publisher),
):
    result = detections.ingest_detection(session, payload, provider, publisher)
    if schedule_photo(session, result.shipment.id, request, background_tasks):
        result.shipment.photo_status = "pending"
    return result


@camera_router.post(
    "/frame",
    response_model=CameraFrameResult,
    dependencies=[Depends(RequirePermission("detections:create", allow_ingest_key=True))],
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {"image/jpeg": {"schema": {"type": "string", "format": "binary"}}},
        }
    },
)
async def ingest_camera_frame(
    metadata: Annotated[CameraFrameInput, Query()],
    request: Request,
    background_tasks: BackgroundTasks,
    frame: bytes = Depends(jpeg_frame),
    session: Session = Depends(get_session),
    provider: TrackingProvider = Depends(get_provider),
    publisher: NotificationPublisher = Depends(get_publisher),
):
    try:
        result = await run_in_threadpool(
            detections.ingest_frame, frame, metadata, session, provider, publisher
        )
        for detection in result.detections:
            schedule_photo(session, detection.shipment_id, request, background_tasks)
        return result
    except InvalidCameraFrame as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
