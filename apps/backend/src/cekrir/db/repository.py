from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import or_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from cekrir.db.model import (
    CameraDevice,
    CctvCamera,
    EspDevice,
    Location,
    LocationMember,
    Notification,
    Role,
    Shipment,
    ShipmentSource,
    ShipmentStatus,
    User,
)
from cekrir.schemas import (
    NotificationRead,
    PackageRead,
    ShipmentRead,
    TrackingSnapshot,
    VisibleShipment,
)
from cekrir.validation.shipments import DetectionInput, ExpectedPackageInput, ResiInput


def visible_shipment(user_id: UUID):
    membership = (
        select(LocationMember.location_id)
        .where(LocationMember.location_id == Location.id, LocationMember.user_id == user_id)
        .exists()
    )
    locations = select(Location.id).where(or_(Location.admin_user_id == user_id, membership))
    return or_(Shipment.location_id.is_(None), Shipment.location_id.in_(locations))


def shipment_view(row: Shipment) -> VisibleShipment:
    if row.location_id is not None:
        return PackageRead.model_validate(row)
    return ShipmentRead.model_validate(row)


class ShipmentRepository:
    def __init__(self, session: Session):
        self.session = session

    def list_shipments(self, user_id: UUID, limit: int, offset: int) -> list[VisibleShipment]:
        rows = self.session.scalars(
            select(Shipment)
            .where(visible_shipment(user_id))
            .order_by(Shipment.created_at.desc(), Shipment.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return [shipment_view(row) for row in rows]

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
                Shipment.location_id.is_(None),
            )
        )

    def get_shipment(self, shipment_id: str, user_id: UUID) -> Shipment | None:
        try:
            identifier = UUID(shipment_id)
        except ValueError:
            return None
        return self.session.scalar(
            select(Shipment).where(Shipment.id == identifier, visible_shipment(user_id))
        )

    def add_expected(
        self, payload: ExpectedPackageInput, location_id: UUID
    ) -> tuple[PackageRead, bool]:
        statement = (
            pg_insert(Shipment)
            .values(
                location_id=location_id,
                courier=payload.courier,
                resi_number=payload.resi_number,
                sender_name=payload.sender_name or None,
                product_names=payload.product_names,
                source=ShipmentSource.MANUAL,
                status=ShipmentStatus.PENDING,
                summary="Menunggu paket tiba.",
                provider="manual",
            )
            .on_conflict_do_nothing(index_elements=["courier", "resi_number", "location_id"])
            .returning(Shipment)
        )
        created = self.session.scalar(statement)
        if created is not None:
            return PackageRead.model_validate(created), True
        existing = self.session.scalars(
            select(Shipment).where(
                Shipment.location_id == location_id,
                Shipment.courier == payload.courier,
                Shipment.resi_number == payload.resi_number,
            )
        ).one()
        return PackageRead.model_validate(existing), False

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

    def claim_photo(self, shipment_id: UUID) -> bool:
        """Allow only one scan to queue the first delivery photo for a shipment."""
        with self.session.begin():
            claimed = self.session.scalar(
                update(Shipment)
                .where(Shipment.id == shipment_id, Shipment.photo_status == "not_requested")
                .values(photo_status="pending")
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
                .on_conflict_do_nothing(index_elements=["courier", "resi_number", "location_id"])
                .returning(Shipment.id)
            )
            shipment_id = self.session.scalar(statement)
            if shipment_id is None:
                existing = self.session.scalar(
                    select(Shipment)
                    .where(
                        Shipment.courier == payload.courier,
                        Shipment.resi_number == payload.resi_number,
                        Shipment.location_id.is_(None),
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
    ) -> tuple[VisibleShipment, NotificationRead | None]:
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
            if previous_status != shipment.status and shipment.location_id is None:
                arrived = shipment.status == ShipmentStatus.DELIVERED
                changed_notification = self._notify(
                    shipment, "Package arrived" if arrived else "Package status changed"
                )
        return (
            shipment_view(shipment),
            NotificationRead.model_validate(changed_notification) if changed_notification else None,
        )

    def _notify(self, shipment: Shipment, title: str, *, arrived: bool = False) -> Notification:
        location_id = None
        if shipment.camera_id:
            location_id = self.session.scalar(
                select(EspDevice.location_id).where(EspDevice.device_id == shipment.camera_id)
            )
            if location_id is None:
                location_id = self.session.scalar(
                    select(CameraDevice.location_id).where(
                        CameraDevice.camera_id == shipment.camera_id
                    )
                )
            if location_id is None:
                try:
                    camera_uuid = UUID(shipment.camera_id)
                except ValueError:
                    camera_uuid = None
                if camera_uuid:
                    location_id = self.session.scalar(
                        select(CctvCamera.location_id).where(CctvCamera.id == camera_uuid)
                    )
        notification = Notification(
            shipment_id=shipment.id,
            location_id=location_id,
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
