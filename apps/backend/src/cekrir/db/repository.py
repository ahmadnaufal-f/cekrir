from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from cekrir.db.model import (
    CameraDevice,
    CctvCamera,
    EspDevice,
    Notification,
    Role,
    Shipment,
    ShipmentSource,
    ShipmentStatus,
    User,
)
from cekrir.schemas import (
    NotificationRead,
    ShipmentRead,
    TrackingSnapshot,
)
from cekrir.validation.shipments import DetectionInput, ResiInput


def detection_location_id(session: Session, source_id: str) -> UUID | None:
    location_id = session.scalar(
        select(EspDevice.location_id).where(EspDevice.device_id == source_id)
    )
    if location_id is not None:
        return location_id
    location_id = session.scalar(
        select(CameraDevice.location_id).where(CameraDevice.camera_id == source_id)
    )
    if location_id is not None:
        return location_id
    try:
        camera_id = UUID(source_id)
    except ValueError:
        return None
    return session.scalar(select(CctvCamera.location_id).where(CctvCamera.id == camera_id))


class ShipmentRepository:
    def __init__(self, session: Session):
        self.session = session

    def list_shipments(self, limit: int, offset: int) -> list[ShipmentRead]:
        rows = self.session.scalars(
            select(Shipment)
            .order_by(Shipment.created_at.desc(), Shipment.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return [ShipmentRead.model_validate(row) for row in rows]

    def list_notifications(self, limit: int, offset: int) -> list[NotificationRead]:
        rows = self.session.scalars(
            select(Notification)
            .order_by(Notification.created_at.desc(), Notification.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return [NotificationRead.model_validate(row) for row in rows]

    def find_shipment(self, payload: ResiInput) -> Shipment | None:
        return self.session.scalar(
            select(Shipment).where(
                Shipment.courier == payload.courier,
                Shipment.resi_number == payload.resi_number,
            )
        )

    def get_shipment(self, shipment_id: str) -> Shipment | None:
        try:
            identifier = UUID(shipment_id)
        except ValueError:
            return None
        return self.session.get(Shipment, identifier)

    def record_detection(
        self, shipment_id: UUID, payload: DetectionInput
    ) -> tuple[ShipmentRead, NotificationRead | None]:
        notification = None
        with self.session.begin():
            shipment = self.session.scalar(
                select(Shipment).where(Shipment.id == shipment_id).with_for_update()
            )
            if shipment is None:
                raise RuntimeError("Shipment disappeared while recording a camera detection")
            first_detection = shipment.last_detected_at is None
            shipment.camera_id = payload.camera_id
            shipment.last_detected_at = datetime.now(UTC)
            if shipment.status != ShipmentStatus.DELIVERED or first_detection:
                shipment.status = ShipmentStatus.DELIVERED
                notification = self._notify(shipment, "Package arrived", arrived=True)
        return ShipmentRead.model_validate(shipment), (
            NotificationRead.model_validate(notification) if notification else None
        )

    def claim_photo(self, shipment_id: UUID, location_id: UUID | None) -> bool:
        """Allow only one scan to queue the first delivery photo for a shipment."""
        claimed = self.session.scalar(
            update(Shipment)
            .where(Shipment.id == shipment_id, Shipment.photo_status == "not_requested")
            .values(photo_status="pending", photo_location_id=location_id)
            .returning(Shipment.id)
        )
        return claimed is not None

    def finish_photo(self, shipment_id: UUID, *, ready: bool) -> None:
        with self.session.begin():
            self.session.execute(
                update(Shipment)
                .where(Shipment.id == shipment_id, Shipment.photo_status == "pending")
                .values(
                    photo_status="ready" if ready else "unavailable",
                    photo_captured_at=datetime.now(UTC) if ready else None,
                )
            )

    def register(
        self, payload: ResiInput, snapshot: TrackingSnapshot, provider: str
    ) -> tuple[ShipmentRead, bool, NotificationRead | None]:
        camera = isinstance(payload, DetectionInput)
        created_notification = None
        with self.session.begin():
            statement = (
                pg_insert(Shipment)
                .values(
                    resi_number=payload.resi_number,
                    courier=payload.courier,
                    source=ShipmentSource.CAMERA if camera else ShipmentSource.MANUAL,
                    camera_id=payload.camera_id if camera else None,
                    status=ShipmentStatus.DELIVERED if camera else ShipmentStatus(snapshot.status),
                    summary="Package detected at location" if camera else snapshot.summary,
                    provider=provider,
                    history=[event.model_dump(mode="json") for event in snapshot.history],
                    last_detected_at=datetime.now(UTC) if camera else None,
                )
                .on_conflict_do_nothing(index_elements=["courier", "resi_number"])
                .returning(Shipment.id)
            )
            shipment_id = self.session.scalar(statement)
            if shipment_id is None:
                existing = self.session.scalar(
                    select(Shipment)
                    .where(
                        Shipment.courier == payload.courier,
                        Shipment.resi_number == payload.resi_number,
                    )
                    .with_for_update()
                )
                if existing is None:
                    raise RuntimeError("Conflicting shipment could not be found")
                if camera:
                    first_detection = existing.last_detected_at is None
                    existing.camera_id = payload.camera_id
                    existing.last_detected_at = datetime.now(UTC)
                    if existing.status != ShipmentStatus.DELIVERED or first_detection:
                        existing.status = ShipmentStatus.DELIVERED
                        created_notification = self._notify(
                            existing, "Package arrived", arrived=True
                        )
                shipment = existing
                created = False
            else:
                shipment = self.session.get(Shipment, shipment_id)
                if shipment is None:
                    raise RuntimeError("Registered shipment could not be loaded")
                created_notification = self._notify(
                    shipment, "Package arrived" if camera else "Package added", arrived=camera
                )
                created = True
        return (
            ShipmentRead.model_validate(shipment),
            created,
            NotificationRead.model_validate(created_notification) if created_notification else None,
        )

    def refresh(
        self, shipment_id: UUID, snapshot: TrackingSnapshot, provider: str
    ) -> tuple[ShipmentRead, NotificationRead | None]:
        changed_notification = None
        with self.session.begin():
            shipment = self.session.scalar(
                select(Shipment).where(Shipment.id == shipment_id).with_for_update()
            )
            if shipment is None:
                raise LookupError("Shipment not found")
            previous_status = shipment.status
            shipment.status = (
                ShipmentStatus.DELIVERED
                if shipment.last_detected_at is not None
                else ShipmentStatus(snapshot.status)
            )
            shipment.summary = snapshot.summary
            shipment.provider = provider
            shipment.history = [event.model_dump(mode="json") for event in snapshot.history]
            shipment.checked_at = datetime.now(UTC)
            if previous_status != shipment.status:
                arrived = shipment.status == ShipmentStatus.DELIVERED
                changed_notification = self._notify(
                    shipment, "Package arrived" if arrived else "Package status changed"
                )
        return (
            ShipmentRead.model_validate(shipment),
            NotificationRead.model_validate(changed_notification) if changed_notification else None,
        )

    def _notify(self, shipment: Shipment, title: str, *, arrived: bool = False) -> Notification:
        notification = Notification(
            shipment_id=shipment.id,
            location_id=(
                detection_location_id(self.session, shipment.camera_id)
                if shipment.camera_id
                else None
            ),
            title=title,
            message=(
                f"{shipment.courier.upper()} | {shipment.resi_number}: "
                f"{'Package detected at location' if arrived else shipment.summary}"
            ),
        )
        self.session.add(notification)
        self.session.flush()
        return notification


class UserRepository:
    def __init__(self, session: Session):
        self.session = session

    def by_email(self, email: str) -> User | None:
        return self.session.scalar(select(User).where(User.email == email.lower()))

    def by_id(self, user_id: UUID) -> User | None:
        return self.session.get(User, user_id)

    def role_by_code(self, code: str) -> Role:
        role = self.session.scalar(select(Role).where(Role.code == code))
        if role is None:
            raise RuntimeError(f"Required role is missing: {code}")
        return role

    def list_users(self) -> list[User]:
        return list(self.session.scalars(select(User).order_by(User.email.asc())))
