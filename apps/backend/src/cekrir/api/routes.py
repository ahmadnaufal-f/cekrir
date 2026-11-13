from fastapi import APIRouter, Depends, HTTPException, Query, Response

from cekrir.api.dependencies import get_provider, get_repository, require_ingest_key
from cekrir.repository import ShipmentRepository
from cekrir.schemas import (
    DetectionInput,
    DetectionResult,
    NotificationRead,
    ResiInput,
    ShipmentRead,
)
from cekrir.services.shipments import refresh_shipment, register_shipment
from cekrir.services.tracking import TrackingProvider

router = APIRouter(prefix="/api/v1")


@router.get("/shipments", response_model=list[ShipmentRead], tags=["shipments"])
def list_shipments(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    repository: ShipmentRepository = Depends(get_repository),
):
    return repository.list_shipments(limit, offset)


@router.post("/shipments", response_model=ShipmentRead, status_code=201, tags=["shipments"])
def create_shipment(
    payload: ResiInput,
    response: Response,
    repository: ShipmentRepository = Depends(get_repository),
    provider: TrackingProvider = Depends(get_provider),
):
    shipment, created = register_shipment(repository, payload, provider)
    response.status_code = 201 if created else 200
    return shipment


@router.post("/shipments/{shipment_id}/refresh", response_model=ShipmentRead, tags=["shipments"])
def check_shipment(
    shipment_id: str,
    repository: ShipmentRepository = Depends(get_repository),
    provider: TrackingProvider = Depends(get_provider),
):
    shipment = repository.get_shipment(shipment_id)
    if shipment is None:
        raise HTTPException(status_code=404, detail="Shipment not found")
    return refresh_shipment(repository, shipment, provider)


@router.post(
    "/detections",
    response_model=DetectionResult,
    dependencies=[Depends(require_ingest_key)],
    tags=["detections"],
)
def ingest_detection(
    payload: DetectionInput,
    repository: ShipmentRepository = Depends(get_repository),
    provider: TrackingProvider = Depends(get_provider),
):
    shipment, created = register_shipment(repository, payload, provider)
    return DetectionResult(created=created, shipment=shipment)


@router.get("/notifications", response_model=list[NotificationRead], tags=["notifications"])
def list_notifications(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    repository: ShipmentRepository = Depends(get_repository),
):
    return repository.list_notifications(limit, offset)
