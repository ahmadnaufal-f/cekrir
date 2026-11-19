from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from cekrir.db.session import get_session
from cekrir.dependencies import get_provider, get_publisher
from cekrir.schemas import CameraFrameResult, DetectionResult
from cekrir.services import detections
from cekrir.services.barcodes import InvalidCameraFrame
from cekrir.services.notifications import NotificationPublisher
from cekrir.services.tracking import TrackingProvider
from cekrir.validation.camera import jpeg_frame
from cekrir.validation.shipments import CameraFrameInput, DetectionInput

router = APIRouter(prefix="/api/v1", tags=["detections"])
camera_router = APIRouter(prefix="/api/v1/detections", tags=["detections"])


@router.post("/detections", response_model=DetectionResult)
def ingest_detection(
    payload: DetectionInput,
    session: Session = Depends(get_session),
    provider: TrackingProvider = Depends(get_provider),
    publisher: NotificationPublisher = Depends(get_publisher),
):
    return detections.ingest_detection(session, payload, provider, publisher)


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
    metadata: Annotated[CameraFrameInput, Query()],
    frame: bytes = Depends(jpeg_frame),
    session: Session = Depends(get_session),
    provider: TrackingProvider = Depends(get_provider),
    publisher: NotificationPublisher = Depends(get_publisher),
):
    try:
        return await run_in_threadpool(
            detections.ingest_frame, frame, metadata, session, provider, publisher
        )
    except InvalidCameraFrame as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
