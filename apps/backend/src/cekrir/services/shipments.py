from uuid import UUID

from sqlalchemy.orm import Session

from cekrir.db.repository import ShipmentRepository, UserRepository, shipment_view
from cekrir.schemas import (
    NotificationRead,
    PackageRead,
    ShipmentRead,
    TrackingSnapshot,
    VisibleShipment,
)
from cekrir.services.accounts import location_for_user
from cekrir.services.notifications import NotificationPublisher
from cekrir.services.tracking import TrackingProvider
from cekrir.validation.shipments import DetectionInput, ExpectedPackageInput, ResiInput


class ShipmentNotFound(Exception):
    pass


class ShipmentLocationUnavailable(Exception):
    pass


def add_expected_package(
    session: Session, user_id: UUID, payload: ExpectedPackageInput
) -> tuple[PackageRead, bool]:
    with session.begin():
        user = UserRepository(session).by_id(user_id)
        location_id, _ = location_for_user(session, user) if user else (None, None)
        if location_id is None:
            raise ShipmentLocationUnavailable("No receiving location is assigned to this account")
        return ShipmentRepository(session).add_expected(payload, location_id)


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
            shipment, notification = repository.record_detection(existing_id, payload)
            return shipment, False, notification
        return existing_read, False, None

    # End the read transaction before making the upstream network request.
    session.rollback()
    if isinstance(payload, DetectionInput):
        snapshot = TrackingSnapshot(status="delivered", summary="Package detected at location")
        return repository.register(payload, snapshot, "device")
    snapshot = provider.lookup(payload.resi_number, payload.courier)
    return repository.register(payload, snapshot, provider.name)


def refresh_shipment(
    session: Session, shipment: ShipmentRead, provider: TrackingProvider
) -> tuple[VisibleShipment, NotificationRead | None]:
    snapshot = provider.lookup(shipment.resi_number, shipment.courier)
    return ShipmentRepository(session).refresh(shipment.id, snapshot, provider.name)


def list_shipments(
    session: Session, user_id: UUID, limit: int, offset: int
) -> list[VisibleShipment]:
    return ShipmentRepository(session).list_shipments(user_id, limit, offset)


def get_shipment(session: Session, shipment_id: str, user_id: UUID) -> VisibleShipment:
    model = ShipmentRepository(session).get_shipment(shipment_id, user_id)
    if model is None:
        session.rollback()
        raise ShipmentNotFound("Shipment not found")
    shipment = shipment_view(model)
    session.rollback()
    return shipment


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
    session: Session,
    shipment_id: str,
    user_id: UUID,
    provider: TrackingProvider,
    publisher: NotificationPublisher,
) -> VisibleShipment:
    shipment = get_shipment(session, shipment_id, user_id)
    try:
        updated, notification = refresh_shipment(session, shipment, provider)
    except LookupError as exc:
        raise ShipmentNotFound("Shipment not found") from exc
    if notification:
        publisher.publish(notification)
    return updated
