import asyncio

from fastapi import WebSocket
from redis import Redis
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from cekrir.config import Settings
from cekrir.db.repository import ShipmentRepository
from cekrir.schemas import NotificationRead
from cekrir.services.auth import authenticate_token
from cekrir.services.email_notifications import EmailNotificationPublisher
from cekrir.services.frontend_notifications import (
    NOTIFICATION_CHANNEL,
    FrontendNotificationPublisher,
)


class NotificationPublisher:
    def __init__(self, client: Redis, settings: Settings | None = None, session_factory=None):
        self.frontend = FrontendNotificationPublisher(client)
        self.email = EmailNotificationPublisher(settings, session_factory)

    def publish(self, notification: NotificationRead) -> None:
        self.frontend.publish(notification)
        self.email.publish(notification)


class NotificationAuthenticationRequired(Exception):
    pass


def list_notifications(session: Session, limit: int, offset: int) -> list[NotificationRead]:
    return ShipmentRepository(session).list_notifications(limit, offset)


async def stream_notifications(websocket: WebSocket) -> None:
    authorization = websocket.headers.get("authorization", "")
    scheme, separator, header_token = authorization.partition(" ")
    token = header_token.strip() if separator and scheme.lower() == "bearer" else None
    token = token or websocket.query_params.get("token")
    principal = None
    if token:
        principal = await run_in_threadpool(
            authenticate_token,
            token,
            websocket.app.state.settings,
            websocket.app.state.session_factory,
        )
    if principal is None or "notifications:read" not in principal["permissions"]:
        raise NotificationAuthenticationRequired()

    await websocket.accept()
    async with websocket.app.state.redis.async_client.pubsub() as pubsub:
        await pubsub.subscribe(NOTIFICATION_CHANNEL)
        await websocket.send_json({"type": "ready"})
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message and message.get("type") == "message":
                await websocket.send_text(message["data"])
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=0.01)
            except TimeoutError:
                pass
