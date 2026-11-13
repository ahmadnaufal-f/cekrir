from cekrir.repository import ShipmentRepository
from cekrir.schemas import DetectionInput, ResiInput, ShipmentRead
from cekrir.services.tracking import TrackingProvider


def register_shipment(
    repository: ShipmentRepository, payload: ResiInput, provider: TrackingProvider
) -> tuple[ShipmentRead, bool]:
    existing = repository.find_shipment(payload)
    if existing:
        if isinstance(payload, DetectionInput):
            existing = repository.record_detection(existing, payload)
        return existing, False

    snapshot = provider.lookup(payload.resi_number, payload.courier)
    return repository.register(payload, snapshot, provider.name)


def refresh_shipment(
    repository: ShipmentRepository, shipment: ShipmentRead, provider: TrackingProvider
) -> ShipmentRead:
    snapshot = provider.lookup(shipment.resi_number, shipment.courier)
    return repository.refresh(shipment, snapshot, provider.name)
