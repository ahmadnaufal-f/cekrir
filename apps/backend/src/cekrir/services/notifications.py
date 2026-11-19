import asyncio
import logging

from fastapi import WebSocket
from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from cekrir.db.repository import ShipmentRepository
from cekrir.schemas import NotificationRead
from cekrir.services.auth import authenticate_token

logger = logging.getLogger(__name__)
NOTIFICATION_CHANNEL = "cekrir:notifications"


class NotificationPublisher:
    def __init__(self, client: Redis):
        self.client = client

    def publish(self, notification: NotificationRead) -> None:
        try:
            self.client.publish(NOTIFICATION_CHANNEL, notification.model_dump_json())
        except RedisError:
            # The database row is durable; a transient Redis failure must not lose it.
            logger.warning("Could not publish live notification event")


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
