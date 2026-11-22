"""User FCM registration and best-effort location-specific push delivery."""

import hashlib
import logging
from threading import Lock
from uuid import UUID, uuid4

import firebase_admin
from firebase_admin import credentials, exceptions, messaging
from sqlalchemy import or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from cekrir.config import Settings
from cekrir.db.model import (
    FcmDevice,
    FcmDeviceLocation,
    Location,
    LocationMember,
    Notification,
    User,
)
from cekrir.schemas import NotificationRead
from cekrir.validation.devices import FcmRegistration

logger = logging.getLogger(__name__)


class PushLocationNotFound(Exception):
    pass


class PushTokenConflict(Exception):
    pass


def register_token(session: Session, user_id: UUID, payload: FcmRegistration) -> dict:
    membership = (
        select(LocationMember.location_id)
        .where(LocationMember.location_id == payload.location_id, LocationMember.user_id == user_id)
        .exists()
    )
    location = session.scalar(
        select(Location.id).where(
            Location.id == payload.location_id, or_(Location.admin_user_id == user_id, membership)
        )
    )
    if location is None:
        raise PushLocationNotFound("Location not found")
    token = payload.token.get_secret_value()
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    device_id = session.scalar(
        insert(FcmDevice)
        .values(user_id=user_id, token=token, token_hash=token_hash)
        .on_conflict_do_nothing(index_elements=["token_hash"])
        .returning(FcmDevice.id)
    )
    if device_id is None:
        device = session.scalar(
            select(FcmDevice).where(FcmDevice.token_hash == token_hash).with_for_update()
        )
        if device is None or device.user_id != user_id:
            session.rollback()
            raise PushTokenConflict("Device token is already registered to another account")
        device_id = device.id
    session.execute(
        insert(FcmDeviceLocation)
        .values(device_id=device_id, location_id=location)
        .on_conflict_do_nothing()
    )
    session.commit()
    return {"device_id": device_id, "location_id": location}


def unregister_token(session: Session, user_id: UUID, device_id: UUID) -> None:
    device = session.scalar(
        select(FcmDevice).where(FcmDevice.id == device_id, FcmDevice.user_id == user_id)
    )
    if device is None:
        raise PushLocationNotFound("Push device not found")
    session.delete(device)
    session.commit()


def unregister_by_token(session: Session, user_id: UUID, token: str) -> None:
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    device = session.scalar(
        select(FcmDevice).where(FcmDevice.token_hash == token_hash, FcmDevice.user_id == user_id)
    )
    if device is not None:
        session.delete(device)
    session.commit()


class PushNotificationPublisher:
    def __init__(self, settings: Settings, session_factory):
        self.settings = settings
        self.session_factory = session_factory
        self.app = None
        self.lock = Lock()
        self.app_name = f"cekrir-push-{uuid4()}"

    def _app(self):
        if self.app is None:
            with self.lock:
                if self.app is None:
                    self.app = firebase_admin.initialize_app(
                        credentials.Certificate(self.settings.firebase_credentials_file),
                        name=self.app_name,
                    )
        return self.app

    def publish(self, notification: NotificationRead) -> None:
        if notification.title != "Package arrived" or not self.settings.firebase_credentials_file:
            return
        try:
            with self.session_factory() as session:
                location_id = session.scalar(
                    select(Notification.location_id).where(Notification.id == notification.id)
                )
                if location_id is None:
                    return
                member = (
                    select(LocationMember.user_id)
                    .where(
                        LocationMember.location_id == location_id,
                        LocationMember.user_id == FcmDevice.user_id,
                    )
                    .exists()
                )
                tokens = list(
                    session.scalars(
                        select(FcmDevice.token)
                        .join(FcmDeviceLocation, FcmDeviceLocation.device_id == FcmDevice.id)
                        .join(Location, Location.id == FcmDeviceLocation.location_id)
                        .join(User, User.id == FcmDevice.user_id)
                        .where(
                            FcmDeviceLocation.location_id == location_id,
                            User.is_active.is_(True),
                            User.email_verified_at.is_not(None),
                            or_(Location.admin_user_id == FcmDevice.user_id, member),
                        )
                    )
                )
            if not tokens:
                return
            app = self._app()
            for start in range(0, len(tokens), 500):
                result = messaging.send_each_for_multicast(
                    messaging.MulticastMessage(
                        tokens=tokens[start : start + 500],
                        notification=messaging.Notification(
                            title=notification.title, body=notification.message
                        ),
                        data={
                            "type": "delivery.created",
                            "eventId": str(notification.id),
                            "deliveryId": str(notification.shipment_id),
                            "householdId": str(location_id),
                        },
                    ),
                    app=app,
                )
                if result.failure_count:
                    logger.warning("Some FCM push messages failed: count=%s", result.failure_count)
        except (exceptions.FirebaseError, SQLAlchemyError, ValueError, OSError) as exc:
            logger.warning("FCM push unavailable: %s", type(exc).__name__)
