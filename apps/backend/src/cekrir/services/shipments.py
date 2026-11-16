from sqlalchemy.orm import Session

from cekrir.db.repository import ShipmentRepository
from cekrir.schemas import (
    NotificationRead,
    ShipmentRead,
)
from cekrir.services.notifications import NotificationPublisher
from cekrir.services.tracking import TrackingProvider
from cekrir.validation.shipments import DetectionInput, ResiInput


class ShipmentNotFound(Exception):
    pass


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


def list_shipments(session: Session, limit: int, offset: int) -> list[ShipmentRead]:
    return ShipmentRepository(session).list_shipments(limit, offset)


def submit_shipment(
    session: Session,
    payload: ResiInput,
    provider: TrackingProvider,
    publisher: NotificationPublisher,
) -> tuple[ShipmentRead, bool]:
    shipment, created, notification = register_shipment(session, payload, provider)
    if notification:
        publisher.publish(notification)
    return shipment, created


def check_shipment(
    session: Session, shipment_id: str, provider: TrackingProvider, publisher: NotificationPublisher
) -> ShipmentRead:
    model = ShipmentRepository(session).get_shipment(shipment_id)
    if model is None:
        session.rollback()
        raise ShipmentNotFound("Shipment not found")
    shipment = ShipmentRead.model_validate(model)
    session.rollback()
    try:
        updated, notification = refresh_shipment(session, shipment, provider)
    except LookupError as exc:
        raise ShipmentNotFound("Shipment not found") from exc
    if notification:
        publisher.publish(notification)
    return updated
