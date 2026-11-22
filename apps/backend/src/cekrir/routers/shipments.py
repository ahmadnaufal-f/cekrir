from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from cekrir.db.session import get_session
from cekrir.dependencies import get_provider, get_publisher
from cekrir.middleware import RequirePermission
from cekrir.schemas import ShipmentRead
from cekrir.services import binderbyte, shipments
from cekrir.services.cctv_photos import photo_path
from cekrir.services.notifications import NotificationPublisher
from cekrir.services.tracking import TrackingProvider
from cekrir.validation.shipments import ResiInput
from cekrir.validation.tracking import BinderByteInput

router = APIRouter(prefix="/api/v1", tags=["shipments"])


@router.post("/tracking/binderbyte", dependencies=[Depends(RequirePermission("shipments:read"))])
def check_binderbyte(payload: BinderByteInput, request: Request):
    try:
        return binderbyte.check_tracking(request.app.state.settings, payload)
    except binderbyte.BinderByteUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get(
    "/shipments",
    response_model=list[ShipmentRead],
    dependencies=[Depends(RequirePermission("shipments:read"))],
)
def list_shipments(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
):
    return shipments.list_shipments(session, limit, offset)


@router.get(
    "/shipments/{shipment_id}",
    response_model=ShipmentRead,
    dependencies=[Depends(RequirePermission("shipments:read"))],
)
def get_shipment(shipment_id: UUID, session: Session = Depends(get_session)):
    try:
        return shipments.get_shipment(session, str(shipment_id))
    except shipments.ShipmentNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/shipments/{shipment_id}/photo",
    dependencies=[Depends(RequirePermission("shipments:read"))],
)
def get_shipment_photo(
    shipment_id: UUID, request: Request, session: Session = Depends(get_session)
):
    try:
        shipment = shipments.get_shipment(session, str(shipment_id))
    except shipments.ShipmentNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if shipment.photo_status == "pending":
        raise HTTPException(status_code=409, detail="Photo capture is pending")
    if shipment.photo_status != "ready":
        raise HTTPException(status_code=404, detail="Photo is unavailable")
    path = photo_path(request.app.state.settings.cctv_photo_dir, shipment_id)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Photo is unavailable")
    return FileResponse(
        path,
        media_type="image/jpeg",
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
    )


@router.post(
    "/shipments",
    response_model=ShipmentRead,
    status_code=201,
    dependencies=[Depends(RequirePermission("shipments:create"))],
)
def create_shipment(
    payload: ResiInput,
    response: Response,
    session: Session = Depends(get_session),
    provider: TrackingProvider = Depends(get_provider),
    publisher: NotificationPublisher = Depends(get_publisher),
):
    shipment, created = shipments.submit_shipment(session, payload, provider, publisher)
    response.status_code = 201 if created else 200
    return shipment


@router.post(
    "/shipments/{shipment_id}/refresh",
    response_model=ShipmentRead,
    dependencies=[Depends(RequirePermission("shipments:refresh"))],
)
def check_shipment(
    shipment_id: str,
    session: Session = Depends(get_session),
    provider: TrackingProvider = Depends(get_provider),
    publisher: NotificationPublisher = Depends(get_publisher),
):
    try:
        return shipments.check_shipment(session, shipment_id, provider, publisher)
    except shipments.ShipmentNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
