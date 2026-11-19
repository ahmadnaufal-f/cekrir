from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from cekrir.db.session import get_session
from cekrir.dependencies import get_provider, get_publisher
from cekrir.middleware import RequirePermission
from cekrir.schemas import ShipmentRead
from cekrir.services import shipments
from cekrir.services.notifications import NotificationPublisher
from cekrir.services.tracking import TrackingProvider
from cekrir.validation.shipments import ResiInput

router = APIRouter(prefix="/api/v1", tags=["shipments"])


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
