from pydantic import ValidationError
from sqlalchemy.orm import Session

from cekrir.schemas import CameraFrameResult, DetectionResult, FrameDetection
from cekrir.services.barcodes import decode_frame
from cekrir.services.notifications import NotificationPublisher
from cekrir.services.shipments import submit_shipment
from cekrir.services.tracking import TrackingProvider
from cekrir.validation.shipments import CameraFrameInput, DetectionInput


def ingest_detection(
    session: Session,
    payload: DetectionInput,
    provider: TrackingProvider,
    publisher: NotificationPublisher,
) -> DetectionResult:
    shipment, created = submit_shipment(session, payload, provider, publisher)
    return DetectionResult(created=created, shipment=shipment)


def ingest_frame(
    frame: bytes,
    metadata: CameraFrameInput,
    session: Session,
    provider: TrackingProvider,
    publisher: NotificationPublisher,
) -> CameraFrameResult:
    candidates: dict[str, DetectionInput] = {}
    for code in decode_frame(frame):
        try:
            payload = DetectionInput(resi_number=code, **metadata.model_dump())
        except ValidationError:
            continue
        candidates[payload.resi_number] = payload
    if len(candidates) != 1:
        return CameraFrameResult(ambiguous=len(candidates) > 1)
    payload = next(iter(candidates.values()))
    shipment, created = submit_shipment(session, payload, provider, publisher)
    return CameraFrameResult(
        detected_count=1,
        detections=[
            FrameDetection(
                resi_number=shipment.resi_number, shipment_id=shipment.id, created=created
            )
        ],
    )
