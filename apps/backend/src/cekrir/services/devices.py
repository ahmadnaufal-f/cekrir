"""ESP device credentials and encrypted CCTV registration."""

import hashlib
import secrets
from datetime import UTC, datetime
from uuid import UUID

from cryptography.fernet import Fernet
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from cekrir.config import Settings
from cekrir.db.model import CctvCamera, EspDevice
from cekrir.services.location_management import _owned_location
from cekrir.validation.devices import CctvConnection, CctvCreate, CctvUpdate


class DeviceNotFound(Exception):
    pass


class DeviceAuthenticationFailed(Exception):
    pass


class EncryptionNotConfigured(Exception):
    pass


class TuyaCameraNotAvailable(Exception):
    pass


def issue_esp_credential(session: Session, admin_id: UUID, location_id: UUID) -> dict:
    _owned_location(session, location_id, admin_id)
    esp = session.scalar(
        select(EspDevice).where(EspDevice.location_id == location_id).with_for_update()
    )
    if esp is None:
        raise DeviceNotFound("ESP is not assigned to this location")
    secret = secrets.token_urlsafe(32)
    esp.credential_hash = hashlib.sha256(secret.encode()).hexdigest()
    esp.last_seen_at = None
    device_id = esp.device_id
    session.commit()
    return {"device_id": device_id, "device_key": secret}


def authenticate_esp(session: Session, device_id: str, device_key: str | None) -> tuple[str, UUID]:
    esp = session.get(EspDevice, device_id)
    candidate = hashlib.sha256((device_key or "").encode()).hexdigest()
    expected = esp.credential_hash if esp and esp.credential_hash else "0" * 64
    if not device_key or not secrets.compare_digest(candidate, expected) or esp is None:
        raise DeviceAuthenticationFailed("Invalid device credentials")
    esp.last_seen_at = datetime.now(UTC)
    session.commit()
    return device_id, esp.location_id


def _cipher(settings: Settings) -> Fernet:
    if not settings.cctv_encryption_key:
        raise EncryptionNotConfigured("CCTV encryption key is not configured")
    try:
        return Fernet(settings.cctv_encryption_key.get_secret_value().encode("ascii"))
    except (ValueError, UnicodeEncodeError) as exc:
        raise EncryptionNotConfigured("CCTV encryption key is invalid") from exc


def _set_cctv_connection(camera: CctvCamera, settings: Settings, payload: CctvConnection) -> None:
    cipher = _cipher(settings)
    camera.stream_url_encrypted = cipher.encrypt(payload.stream_url.encode()).decode()
    camera.username_encrypted = cipher.encrypt(
        payload.username.get_secret_value().encode()
    ).decode()
    camera.password_encrypted = cipher.encrypt(
        payload.password.get_secret_value().encode()
    ).decode()


def _set_tuya_device(
    session: Session, settings: Settings, camera: CctvCamera, device_id: str | None
) -> None:
    if device_id == camera.tuya_device_id:
        return
    if device_id is not None:
        if device_id not in settings.tuya_location_devices.get(camera.location_id, ()):
            raise TuyaCameraNotAvailable("Tuya device is unavailable for this location")
        if session.scalar(select(CctvCamera.id).where(CctvCamera.tuya_device_id == device_id)):
            raise TuyaCameraNotAvailable("Tuya device is already linked to a camera")
    else:
        camera.is_delivery_camera = False
    camera.tuya_device_id = device_id


def _cctv_at_location(session: Session, location_id: UUID, camera_id: UUID) -> CctvCamera:
    camera = session.scalar(
        select(CctvCamera).where(CctvCamera.id == camera_id, CctvCamera.location_id == location_id)
    )
    if camera is None:
        raise DeviceNotFound("CCTV camera not found")
    return camera


def add_cctv(
    session: Session, settings: Settings, admin_id: UUID, location_id: UUID, payload: CctvCreate
) -> CctvCamera:
    _owned_location(session, location_id, admin_id, for_update=True)
    camera = CctvCamera(location_id=location_id, name=payload.name)
    _set_cctv_connection(camera, settings, payload)
    _set_tuya_device(session, settings, camera, payload.tuya_device_id)
    session.add(camera)
    session.commit()
    return camera


def list_cctv(session: Session, admin_id: UUID, location_id: UUID) -> list[CctvCamera]:
    _owned_location(session, location_id, admin_id)
    return list(
        session.scalars(
            select(CctvCamera)
            .where(CctvCamera.location_id == location_id)
            .order_by(CctvCamera.name, CctvCamera.id)
        )
    )


def update_cctv(
    session: Session,
    settings: Settings,
    admin_id: UUID,
    location_id: UUID,
    camera_id: UUID,
    payload: CctvUpdate,
) -> CctvCamera:
    _owned_location(session, location_id, admin_id, for_update=True)
    camera = _cctv_at_location(session, location_id, camera_id)
    camera.name = payload.name
    if "tuya_device_id" in payload.model_fields_set:
        _set_tuya_device(session, settings, camera, payload.tuya_device_id)
    if payload.connection:
        _set_cctv_connection(camera, settings, payload.connection)
    session.commit()
    return camera


def select_delivery_camera(
    session: Session, settings: Settings, admin_id: UUID, location_id: UUID, camera_id: UUID
) -> CctvCamera:
    _owned_location(session, location_id, admin_id, for_update=True)
    camera = _cctv_at_location(session, location_id, camera_id)
    if camera.tuya_device_id not in settings.tuya_location_devices.get(location_id, ()):
        raise TuyaCameraNotAvailable("Link an authorized Tuya device before selecting this camera")
    if not camera.is_delivery_camera:
        session.execute(
            update(CctvCamera)
            .where(CctvCamera.location_id == location_id, CctvCamera.is_delivery_camera)
            .values(is_delivery_camera=False)
        )
        camera.is_delivery_camera = True
    session.commit()
    return camera
