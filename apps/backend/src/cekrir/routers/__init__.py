from cekrir.routers.auth import router as auth_router
from cekrir.routers.detections import camera_router
from cekrir.routers.detections import router as detection_router
from cekrir.routers.notifications import router as notification_router
from cekrir.routers.shipments import router as shipment_router

__all__ = [
    "auth_router",
    "camera_router",
    "detection_router",
    "notification_router",
    "shipment_router",
]
