from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Request, Response, status
from sqlalchemy.orm import Session

from cekrir.db.session import get_session
from cekrir.dependencies import get_user_id
from cekrir.middleware import RequirePermission
from cekrir.schemas import LocationRead
from cekrir.services import devices, location_management
from cekrir.validation.devices import CctvCreate
from cekrir.validation.locations import LocationCreate

router = APIRouter(prefix="/api/v1/locations", tags=["locations"])


@router.post(
    "/{location_id}/esp/credentials", dependencies=[Depends(RequirePermission("locations:manage"))]
)
def provision_esp(
    location_id: UUID,
    response: Response,
    admin_id: UUID = Depends(get_user_id),
    session: Session = Depends(get_session),
):
    try:
        result = devices.issue_esp_credential(session, admin_id, location_id)
    except (devices.DeviceNotFound, location_management.LocationResourceNotFound) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    response.headers["Cache-Control"] = "no-store"
    return result


@router.post(
    "/{location_id}/cctv",
    status_code=201,
    dependencies=[Depends(RequirePermission("locations:manage"))],
)
def create_cctv(
    location_id: UUID,
    payload: CctvCreate,
    request: Request,
    admin_id: UUID = Depends(get_user_id),
    session: Session = Depends(get_session),
):
    try:
        return devices.add_cctv(session, request.app.state.settings, admin_id, location_id, payload)
    except location_management.LocationResourceNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except devices.EncryptionNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/{location_id}/cctv", dependencies=[Depends(RequirePermission("locations:manage"))])
def get_cctv(
    location_id: UUID,
    admin_id: UUID = Depends(get_user_id),
    session: Session = Depends(get_session),
):
    try:
        return devices.list_cctv(session, admin_id, location_id)
    except location_management.LocationResourceNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "",
    response_model=list[LocationRead],
    dependencies=[Depends(RequirePermission("locations:manage"))],
)
def list_locations(admin_id: UUID = Depends(get_user_id), session: Session = Depends(get_session)):
    return location_management.list_owned_locations(session, admin_id)


@router.post(
    "",
    response_model=LocationRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RequirePermission("locations:manage"))],
)
def create_location(
    payload: LocationCreate,
    admin_id: UUID = Depends(get_user_id),
    session: Session = Depends(get_session),
):
    try:
        return location_management.create_location(session, admin_id, payload)
    except location_management.LocationResourceNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put(
    "/{location_id}/esp/{device_id}", dependencies=[Depends(RequirePermission("locations:manage"))]
)
def assign_esp(
    location_id: UUID,
    device_id: Annotated[
        str, Path(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
    ],
    admin_id: UUID = Depends(get_user_id),
    session: Session = Depends(get_session),
):
    try:
        location_management.assign_esp(session, location_id, admin_id, device_id)
    except location_management.LocationResourceNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except location_management.EspAlreadyAssigned as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"detail": "ESP assigned"}


@router.delete("/{location_id}/esp", dependencies=[Depends(RequirePermission("locations:manage"))])
def remove_esp(
    location_id: UUID,
    admin_id: UUID = Depends(get_user_id),
    session: Session = Depends(get_session),
):
    try:
        location_management.remove_esp(session, location_id, admin_id)
    except location_management.LocationResourceNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"detail": "ESP removed; onboarding is incomplete"}


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
