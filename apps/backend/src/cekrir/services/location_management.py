from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from cekrir.db.model import CameraDevice, Location, LocationMember, User


class LocationResourceNotFound(Exception):
    pass


class CameraAlreadyAssigned(Exception):
    pass


def list_owned_locations(session: Session, admin_id: UUID) -> list[dict]:
    locations = session.scalars(
        select(Location).where(Location.admin_user_id == admin_id).order_by(Location.name)
    )
    return [{"id": location.id, "name": location.name} for location in locations]


def _owned_location(session: Session, location_id: UUID, admin_id: UUID) -> Location:
    location = session.scalar(
        select(Location).where(Location.id == location_id, Location.admin_user_id == admin_id)
    )
    if location is None:
        raise LocationResourceNotFound("Location not found")
    return location


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
