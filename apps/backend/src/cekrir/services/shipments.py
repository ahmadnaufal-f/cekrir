from sqlalchemy.orm import Session

from cekrir.db.repository import ShipmentRepository
from cekrir.schemas import (
    DetectionInput,
    NotificationRead,
    ResiInput,
    ShipmentRead,
)
from cekrir.services.tracking import TrackingProvider


def register_shipment(
    session: Session, payload: ResiInput, provider: TrackingProvider
) -> tuple[ShipmentRead, bool, NotificationRead | None]:
    repository = ShipmentRepository(session)
    existing = repository.find_shipment(payload)
    if existing:
        existing_id = existing.id
        existing_read = ShipmentRead.model_validate(existing)
        session.rollback()
        if isinstance(payload, DetectionInput):
            shipment = repository.record_detection(existing_id, payload)
            return shipment, False, None
        return existing_read, False, None

    # End the read transaction before making the upstream network request.
    session.rollback()
    snapshot = provider.lookup(payload.resi_number, payload.courier)
    return repository.register(payload, snapshot, provider.name)


def refresh_shipment(
    session: Session, shipment: ShipmentRead, provider: TrackingProvider
) -> tuple[ShipmentRead, NotificationRead | None]:
    snapshot = provider.lookup(shipment.resi_number, shipment.courier)
    return ShipmentRepository(session).refresh(shipment.id, snapshot, provider.name)
