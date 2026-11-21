from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session

from cekrir.db.session import get_session
from cekrir.dependencies import get_user_id
from cekrir.middleware import RequirePermission
from cekrir.services import location_management

router = APIRouter(prefix="/api/v1/locations", tags=["locations"])


@router.get("", dependencies=[Depends(RequirePermission("locations:manage"))])
def list_locations(admin_id: UUID = Depends(get_user_id), session: Session = Depends(get_session)):
    return location_management.list_owned_locations(session, admin_id)


@router.put(
    "/{location_id}/members/{user_id}",
    dependencies=[Depends(RequirePermission("locations:manage"))],
)
def add_member(
    location_id: UUID,
    user_id: UUID,
    admin_id: UUID = Depends(get_user_id),
    session: Session = Depends(get_session),
):
    try:
        location_management.add_member(session, location_id, admin_id, user_id)
    except location_management.LocationResourceNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"detail": "Member assigned"}


@router.put(
    "/{location_id}/cameras/{camera_id}",
    dependencies=[Depends(RequirePermission("locations:manage"))],
)
def add_camera(
    location_id: UUID,
    camera_id: Annotated[str, Path(min_length=1, max_length=100)],
    admin_id: UUID = Depends(get_user_id),
    session: Session = Depends(get_session),
):
    try:
        location_management.add_camera(session, location_id, admin_id, camera_id)
    except location_management.LocationResourceNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except location_management.CameraAlreadyAssigned as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"detail": "Camera assigned"}


@router.delete(
    "/{location_id}/members/{user_id}",
    dependencies=[Depends(RequirePermission("locations:manage"))],
)
def remove_member(
    location_id: UUID,
    user_id: UUID,
    admin_id: UUID = Depends(get_user_id),
    session: Session = Depends(get_session),
):
    try:
        location_management.remove_member(session, location_id, admin_id, user_id)
    except location_management.LocationResourceNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"detail": "Member removed"}


@router.delete(
    "/{location_id}/cameras/{camera_id}",
    dependencies=[Depends(RequirePermission("locations:manage"))],
)
def remove_camera(
    location_id: UUID,
    camera_id: Annotated[str, Path(min_length=1, max_length=100)],
    admin_id: UUID = Depends(get_user_id),
    session: Session = Depends(get_session),
):
    try:
        location_management.remove_camera(session, location_id, admin_id, camera_id)
    except location_management.LocationResourceNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"detail": "Camera removed"}
