import logging

from pydantic import ValidationError
from sqlalchemy.orm import Session

from cekrir.config import Settings
from cekrir.schemas import CameraFrameResult, DetectionResult, FrameDetection
from cekrir.services.barcodes import decode_frame
from cekrir.services.binderbyte import BinderByteUnavailable, check_tracking
from cekrir.services.notifications import NotificationPublisher
from cekrir.services.shipments import register_shipment
from cekrir.services.tracking import TrackingProvider
from cekrir.validation.shipments import (
    CameraCourierInput,
    CameraFrameInput,
    DetectionInput,
    ResiNumberInput,
)
from cekrir.validation.tracking import BinderByteInput

logger = logging.getLogger(__name__)


def ingest_detection(
    session: Session,
    payload: DetectionInput,
    provider: TrackingProvider,
    publisher: NotificationPublisher,
    settings: Settings | None = None,
) -> DetectionResult:
    shipment, created, notification = register_shipment(session, payload, provider)
    if notification:
        publisher.publish(notification)

    tracking = None
    # TODO: Resolve the courier per package instead of using a global setting.
    courier = settings.binderbyte_detection_courier.strip().lower() if settings else ""
    if (
        notification
        and courier
        and courier == payload.courier
        and settings
        and settings.binderbyte_api_key
        and settings.binderbyte_api_key.get_secret_value().strip()
    ):
        try:
            tracking = check_tracking(
                settings, BinderByteInput(resi_number=payload.resi_number, courier=courier)
            )
        except BinderByteUnavailable:
            logger.warning("BinderByte tracking unavailable for a package detection")
    return DetectionResult(created=created, shipment=shipment, tracking=tracking)


def ingest_frame(
    frame: bytes,
    metadata: CameraFrameInput,
    session: Session,
    provider: TrackingProvider,
    publisher: NotificationPublisher,
    settings: Settings | None = None,
) -> CameraFrameResult:
    candidates: dict[str, str] = {}
    for code in decode_frame(frame):
        try:
            candidate = ResiNumberInput(resi_number=code)
        except ValidationError:
            continue
        candidates[candidate.resi_number] = candidate.resi_number
    if len(candidates) != 1:
        return CameraFrameResult(ambiguous=len(candidates) > 1)
    resi_number = next(iter(candidates.values()))
    if metadata.courier is None:
        # TODO: Identify the courier before creating or matching a shipment.
        return CameraFrameResult(
            detected_count=1, detections=[FrameDetection(resi_number=resi_number, created=False)]
        )
    payload = DetectionInput(resi_number=resi_number, **metadata.model_dump())
    result = ingest_detection(session, payload, provider, publisher, settings)
    return CameraFrameResult(
        detected_count=1,
        detections=[
            FrameDetection(
                resi_number=result.shipment.resi_number,
                shipment_id=result.shipment.id,
                created=result.created,
                tracking=result.tracking,
            )
        ],
    )


def ingest_esp_frame(
    frame: bytes,
    device_id: str,
    metadata: CameraCourierInput,
    session: Session,
    provider: TrackingProvider,
    publisher: NotificationPublisher,
    settings: Settings | None = None,
) -> CameraFrameResult:
    result = ingest_frame(
        frame,
        CameraFrameInput(camera_id=device_id, **metadata.model_dump()),
        session,
        provider,
        publisher,
        settings,
    )
    # Keep the response small for ESP firmware; full tracking is available through
    # /tracking/binderbyte, rather than sending address/history data to the device.
    for detection in result.detections:
        if detection.tracking:
            summary = detection.tracking.get("summary")
            status = summary.get("status") if isinstance(summary, dict) else None
            detection.tracking = {"summary": {"status": str(status)[:128]}} if status else {}
    return result
