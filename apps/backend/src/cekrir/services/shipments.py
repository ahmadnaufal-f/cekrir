from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from cekrir.models import Notification, Shipment, utc_now
from cekrir.schemas import DetectionInput, ResiInput, TrackingSnapshot
from cekrir.services.tracking import TrackingProvider


def find_shipment(session: Session, payload: ResiInput) -> Shipment | None:
    return session.exec(
        select(Shipment).where(
            Shipment.courier == payload.courier, Shipment.resi_number == payload.resi_number
        )
    ).first()


def apply_snapshot(shipment: Shipment, snapshot: TrackingSnapshot, provider: str) -> None:
    shipment.status = snapshot.status
    shipment.summary = snapshot.summary
    shipment.history = [
        event.model_dump(mode="json", exclude_none=True) for event in snapshot.history
    ]
    shipment.provider = provider
    shipment.checked_at = utc_now()


def register_shipment(
    session: Session, payload: ResiInput, provider: TrackingProvider
) -> tuple[Shipment, bool]:
    existing = find_shipment(session, payload)
    if existing:
        if isinstance(payload, DetectionInput):
            existing.last_detected_at = utc_now()
            existing.camera_id = payload.camera_id
            session.add(existing)
            session.commit()
            session.refresh(existing)
        return existing, False

    snapshot = provider.lookup(payload.resi_number, payload.courier)
    camera = isinstance(payload, DetectionInput)
    shipment = Shipment(
        resi_number=payload.resi_number,
        courier=payload.courier,
        source="camera" if camera else "manual",
        camera_id=payload.camera_id if camera else None,
        last_detected_at=utc_now() if camera else None,
    )
    apply_snapshot(shipment, snapshot, provider.name)
    session.add(shipment)
    session.add(
        Notification(
            shipment_id=shipment.id,
            title="Package detected" if camera else "Package added",
            message=f"{shipment.courier.upper()} · {shipment.resi_number}: {shipment.summary}",
        )
    )
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        # The unique constraint also deduplicates concurrent camera requests.
        existing = find_shipment(session, payload)
        if existing is None:
            raise
        return existing, False
    session.refresh(shipment)
    return shipment, True


def refresh_shipment(session: Session, shipment: Shipment, provider: TrackingProvider) -> Shipment:
    snapshot = provider.lookup(shipment.resi_number, shipment.courier)
    previous_status = shipment.status
    apply_snapshot(shipment, snapshot, provider.name)
    session.add(shipment)
    if previous_status != shipment.status:
        session.add(
            Notification(
                shipment_id=shipment.id,
                title="Package status changed",
                message=f"{shipment.courier.upper()} · {shipment.resi_number}: {shipment.summary}",
            )
        )
    session.commit()
    session.refresh(shipment)
    return shipment
