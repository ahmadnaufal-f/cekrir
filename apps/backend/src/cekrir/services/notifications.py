import asyncio
import hashlib
import logging
from uuid import UUID

from fastapi import WebSocket
from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy import or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from cekrir.config import Settings
from cekrir.db.model import Location, LocationMember, Notification, User
from cekrir.db.repository import ShipmentRepository
from cekrir.schemas import NotificationRead
from cekrir.services.auth import authenticate_token
from cekrir.services.email import EmailUnavailable, send_email

logger = logging.getLogger(__name__)
NOTIFICATION_CHANNEL = "cekrir:notifications"


class NotificationPublisher:
    def __init__(self, client: Redis, settings: Settings | None = None, session_factory=None):
        self.client = client
        self.settings = settings
        self.session_factory = session_factory

    def publish(self, notification: NotificationRead) -> None:
        try:
            self.client.publish(NOTIFICATION_CHANNEL, notification.model_dump_json())
        except RedisError:
            # The database row is durable; a transient Redis failure must not lose it.
            logger.warning("Could not publish live notification event")
        self._send_location_emails(notification)

    def _send_location_emails(self, notification: NotificationRead) -> None:
        if (
            not self.settings
            or self.settings.email_provider != "resend"
            or not self.session_factory
        ):
            return
        if not self.settings.resend_api_key or not self.settings.resend_from:
            return
        try:
            with self.session_factory() as session:
                location_id = session.scalar(
                    select(Notification.location_id).where(Notification.id == notification.id)
                )
                if location_id is None:
                    logger.info("Email notification skipped: no location assigned")
                    return
                location = session.get(Location, location_id)
                if location is None:
                    return
                member_ids = select(LocationMember.user_id).where(
                    LocationMember.location_id == location_id
                )
                recipients = session.execute(
                    select(User.id, User.email).where(
                        User.is_active.is_(True),
                        User.email_verified_at.is_not(None),
                        or_(User.id == location.admin_user_id, User.id.in_(member_ids)),
                    )
                ).all()
        except SQLAlchemyError:
            logger.warning("Could not find notification recipients")
            return
        for user_id, email in recipients:
            try:
                send_email(
                    self.settings,
                    email,
                    notification.title,
                    notification.message,
                    idempotency_key=f"notification/{notification.id}/{user_id}",
                )
            except EmailUnavailable:
                logger.warning("Location notification email could not be sent")


class EmailRecipientNotFound(Exception):
    pass


def send_individual_email(
    session: Session,
    settings: Settings,
    sender_id: UUID,
    user_id: UUID,
    subject: str,
    message: str,
    idempotency_key: str,
) -> None:
    user = session.scalar(
        select(User).where(
            User.id == user_id,
            User.is_active.is_(True),
            User.email_verified_at.is_not(None),
        )
    )
    shared_location = session.scalar(
        select(Location.id)
        .join(LocationMember, LocationMember.location_id == Location.id)
        .where(
            Location.admin_user_id == sender_id,
            LocationMember.user_id == user_id,
        )
        .limit(1)
    )
    if user is None or (sender_id != user_id and shared_location is None):
        raise EmailRecipientNotFound("Recipient not found")
    email = user.email
    session.rollback()
    key = hashlib.sha256(f"{sender_id}:{user_id}:{idempotency_key}".encode()).hexdigest()
    send_email(settings, email, subject, message, idempotency_key=f"individual/{key}")


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
