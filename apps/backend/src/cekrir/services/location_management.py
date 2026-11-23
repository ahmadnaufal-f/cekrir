from uuid import UUID

from sqlalchemy import delete, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from cekrir.db.model import CameraDevice, EspDevice, Location, LocationMember, Role, User
from cekrir.validation.locations import LocationCreate


class LocationResourceNotFound(Exception):
    pass


class CameraAlreadyAssigned(Exception):
    pass


class EspAlreadyAssigned(Exception):
    pass


def list_owned_locations(session: Session, admin_id: UUID) -> list[dict]:
    rows = session.execute(
        select(Location, EspDevice.device_id, EspDevice.last_seen_at)
        .outerjoin(EspDevice, EspDevice.location_id == Location.id)
        .where(Location.admin_user_id == admin_id)
        .order_by(Location.name)
    ).all()
    cameras: dict[UUID, list[str]] = {}
    for location_id, camera_id in session.execute(
        select(CameraDevice.location_id, CameraDevice.camera_id)
        .join(Location, Location.id == CameraDevice.location_id)
        .where(Location.admin_user_id == admin_id)
        .order_by(CameraDevice.camera_id)
    ):
        cameras.setdefault(location_id, []).append(camera_id)
    locations = []
    for location, esp_id, esp_last_seen in rows:
        locations.append(
            {
                "id": location.id,
                "name": location.name,
                "esp_device_id": esp_id,
                "onboarding_complete": esp_last_seen is not None,
                "camera_ids": cameras.get(location.id, []),
            }
        )
    return locations


def create_location(session: Session, admin_id: UUID, payload: LocationCreate) -> dict:
    admin = session.scalar(select(User).join(Role).where(User.id == admin_id, Role.code == "admin"))
    if admin is None:
        raise LocationResourceNotFound("Admin not found")
    location = Location(name=payload.name, admin=admin)
    session.add(location)
    session.commit()
    session.refresh(location)
    return {
        "id": location.id,
        "name": location.name,
        "esp_device_id": None,
        "onboarding_complete": False,
        "camera_ids": [],
    }


def _owned_location(
    session: Session, location_id: UUID, admin_id: UUID, *, for_update: bool = False
) -> Location:
    query = select(Location).where(Location.id == location_id, Location.admin_user_id == admin_id)
    location = session.scalar(query.with_for_update() if for_update else query)
    if location is None:
        raise LocationResourceNotFound("Location not found")
    return location


def can_access_location(session: Session, location_id: UUID, user_id: UUID) -> bool:
    member = (
        select(LocationMember.user_id)
        .where(LocationMember.location_id == Location.id, LocationMember.user_id == user_id)
        .exists()
    )
    return (
        session.scalar(
            select(Location.id).where(
                Location.id == location_id, or_(Location.admin_user_id == user_id, member)
            )
        )
        is not None
    )


def add_member(session: Session, location_id: UUID, admin_id: UUID, user_id: UUID) -> None:
    _owned_location(session, location_id, admin_id)
    if session.get(User, user_id) is None:
        raise LocationResourceNotFound("User not found")
    session.execute(
        insert(LocationMember)
        .values(location_id=location_id, user_id=user_id)
        .on_conflict_do_nothing()
    )
    session.commit()


def add_camera(session: Session, location_id: UUID, admin_id: UUID, camera_id: str) -> None:
    _owned_location(session, location_id, admin_id)
    session.execute(
        insert(CameraDevice)
        .values(location_id=location_id, camera_id=camera_id)
        .on_conflict_do_nothing()
    )
    assigned = session.get(CameraDevice, camera_id)
    if assigned is None or assigned.location_id != location_id:
        session.rollback()
        raise CameraAlreadyAssigned("Camera is already assigned to another location")
    session.commit()


def assign_esp(session: Session, location_id: UUID, admin_id: UUID, device_id: str) -> None:
    _owned_location(session, location_id, admin_id)
    session.execute(
        insert(EspDevice)
        .values(location_id=location_id, device_id=device_id)
        .on_conflict_do_nothing()
    )
    assigned = session.get(EspDevice, device_id)
    if assigned is None or assigned.location_id != location_id:
        session.rollback()
        raise EspAlreadyAssigned("ESP or location is already assigned")
    session.commit()


def remove_esp(session: Session, location_id: UUID, admin_id: UUID) -> None:
    _owned_location(session, location_id, admin_id)
    session.execute(delete(EspDevice).where(EspDevice.location_id == location_id))
    session.commit()


def remove_member(session: Session, location_id: UUID, admin_id: UUID, user_id: UUID) -> None:
    _owned_location(session, location_id, admin_id)
    session.execute(
        delete(LocationMember).where(
            LocationMember.location_id == location_id, LocationMember.user_id == user_id
        )
    )
    session.commit()


def remove_camera(session: Session, location_id: UUID, admin_id: UUID, camera_id: str) -> None:
    _owned_location(session, location_id, admin_id)
    session.execute(
        delete(CameraDevice).where(
            CameraDevice.location_id == location_id, CameraDevice.camera_id == camera_id
        )
    )
    session.commit()
