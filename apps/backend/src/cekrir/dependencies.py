from uuid import UUID

from fastapi import Request

from cekrir.services.notifications import NotificationPublisher
from cekrir.services.tracking import TrackingProvider


def get_provider(request: Request) -> TrackingProvider:
    return request.app.state.tracking_provider


def get_publisher(request: Request) -> NotificationPublisher:
    return request.app.state.notification_publisher


def get_user_id(request: Request) -> UUID:
    return UUID(request.state.principal["id"])
