from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy.orm import Session

from cekrir.db.repository import ShipmentRepository
from cekrir.db.session import get_session
from cekrir.schemas import ResiInput, ShipmentRead
from cekrir.services.notifications import NotificationPublisher
from cekrir.services.shipments import refresh_shipment, register_shipment
from cekrir.services.tracking import TrackingProvider

router = APIRouter(prefix="/api/v1", tags=["shipments"])


def get_provider(request: Request) -> TrackingProvider:
    return request.app.state.tracking_provider


def get_publisher(request: Request) -> NotificationPublisher:
    return request.app.state.notification_publisher


@router.get("/shipments", response_model=list[ShipmentRead])
def list_shipments(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
):
    return ShipmentRepository(session).list_shipments(limit, offset)


@router.post("/shipments", response_model=ShipmentRead, status_code=201)
def create_shipment(
    payload: ResiInput,
    response: Response,
    session: Session = Depends(get_session),
    provider: TrackingProvider = Depends(get_provider),
    publisher: NotificationPublisher = Depends(get_publisher),
):
    shipment, created, notification = register_shipment(session, payload, provider)
    response.status_code = 201 if created else 200
    if notification:
        publisher.publish(notification)
    return shipment


@router.post("/shipments/{shipment_id}/refresh", response_model=ShipmentRead)
def check_shipment(
    shipment_id: str,
    session: Session = Depends(get_session),
    provider: TrackingProvider = Depends(get_provider),
    publisher: NotificationPublisher = Depends(get_publisher),
):
    shipment_model = ShipmentRepository(session).get_shipment(shipment_id)
    if shipment_model is None:
        session.rollback()
        raise HTTPException(status_code=404, detail="Shipment not found")
    shipment = ShipmentRead.model_validate(shipment_model)
    session.rollback()
    updated, notification = refresh_shipment(session, shipment, provider)
    if notification:
        publisher.publish(notification)
    return updated
