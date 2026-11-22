"""ESP device credentials and encrypted CCTV registration."""

import hashlib
import secrets
from datetime import UTC, datetime
from uuid import UUID

from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.orm import Session

from cekrir.config import Settings
from cekrir.db.model import CctvCamera, EspDevice
from cekrir.services.location_management import _owned_location
from cekrir.validation.devices import CctvCreate


class DeviceNotFound(Exception):
    pass


class DeviceAuthenticationFailed(Exception):
    pass


class EncryptionNotConfigured(Exception):
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


def authenticate_esp(session: Session, device_id: str, device_key: str | None) -> str:
    esp = session.get(EspDevice, device_id)
    candidate = hashlib.sha256((device_key or "").encode()).hexdigest()
    expected = esp.credential_hash if esp and esp.credential_hash else "0" * 64
    if not device_key or not secrets.compare_digest(candidate, expected) or esp is None:
        raise DeviceAuthenticationFailed("Invalid device credentials")
    esp.last_seen_at = datetime.now(UTC)
    session.commit()
    return device_id


def _cipher(settings: Settings) -> Fernet:
    if not settings.cctv_encryption_key:
        raise EncryptionNotConfigured("CCTV encryption key is not configured")
    try:
        return Fernet(settings.cctv_encryption_key.get_secret_value().encode("ascii"))
    except (ValueError, UnicodeEncodeError) as exc:
        raise EncryptionNotConfigured("CCTV encryption key is invalid") from exc


def add_cctv(
    session: Session, settings: Settings, admin_id: UUID, location_id: UUID, payload: CctvCreate
) -> dict:
    _owned_location(session, location_id, admin_id)
    cipher = _cipher(settings)
    camera = CctvCamera(
        location_id=location_id,
        name=payload.name,
        stream_url_encrypted=cipher.encrypt(payload.stream_url.encode()).decode(),
        username_encrypted=cipher.encrypt(payload.username.get_secret_value().encode()).decode(),
        password_encrypted=cipher.encrypt(payload.password.get_secret_value().encode()).decode(),
    )
    session.add(camera)
    session.commit()
    session.refresh(camera)
    return {"id": camera.id, "location_id": location_id, "name": camera.name}


def list_cctv(session: Session, admin_id: UUID, location_id: UUID) -> list[dict]:
    _owned_location(session, location_id, admin_id)
    cameras = session.scalars(select(CctvCamera).where(CctvCamera.location_id == location_id))
    return [
        {"id": camera.id, "location_id": camera.location_id, "name": camera.name}
        for camera in cameras
    ]
