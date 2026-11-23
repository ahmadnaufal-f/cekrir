"""Queue a delivery photo after a scan and keep its JPEG in local storage."""

import logging
import os
from pathlib import Path
from typing import Protocol
from uuid import UUID, uuid4

from fastapi import BackgroundTasks, Request
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from cekrir.db.model import CctvCamera
from cekrir.db.repository import ShipmentRepository, detection_location_id
from cekrir.services.location_management import can_access_location

logger = logging.getLogger(__name__)


class PhotoCapturer(Protocol):
    def capture_jpeg(self, device_id: str) -> bytes: ...


def photo_path(photo_dir: Path, shipment_id: UUID) -> Path:
    return photo_dir / f"{shipment_id}.jpg"


def schedule_photo(
    session: Session,
    shipment_id: UUID,
    request: Request,
    background_tasks: BackgroundTasks,
    *,
    location_id: UUID | None = None,
    source_id: str | None = None,
) -> bool:
    capturer: PhotoCapturer | None = getattr(request.app.state, "photo_capturer", None)
    if capturer is None:
        return False
    settings = request.app.state.settings
    device_id = settings.tuya_cctv_device_id
    photo_location_id = None
    try:
        with session.begin():
            if settings.tuya_location_devices:
                if source_id is not None:
                    location_id = detection_location_id(session, source_id)
                allowed_devices = settings.tuya_location_devices.get(location_id)
                if not allowed_devices:
                    return False
                principal = getattr(request.state, "principal", None)
                if principal and not can_access_location(
                    session, location_id, UUID(principal["id"])
                ):
                    return False
                device_id = session.scalar(
                    select(CctvCamera.tuya_device_id).where(
                        CctvCamera.location_id == location_id,
                        CctvCamera.is_delivery_camera,
                        CctvCamera.tuya_device_id.in_(allowed_devices),
                    )
                )
                photo_location_id = location_id
            if device_id is None:
                return False
            claimed = ShipmentRepository(session).claim_photo(shipment_id, photo_location_id)
    except Exception as exc:
        session.rollback()
        logger.warning("Could not queue CCTV photo for %s: %s", shipment_id, type(exc).__name__)
        return False
    if claimed:
        background_tasks.add_task(
            capture_photo_task,
            request.app.state.session_factory,
            capturer,
            device_id,
            settings.cctv_photo_dir,
            shipment_id,
        )
    return claimed


def capture_photo_task(
    sessions: sessionmaker[Session],
    capturer: PhotoCapturer,
    device_id: str,
    photo_dir: Path,
    shipment_id: UUID,
) -> None:
    destination = photo_path(photo_dir, shipment_id)
    saved = False
    try:
        jpeg = capturer.capture_jpeg(device_id)
        photo_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        temporary = photo_dir / f".{shipment_id}.{uuid4().hex}.tmp"
        try:
            fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as output:
                output.write(jpeg)
            os.replace(temporary, destination)
            saved = True
        finally:
            temporary.unlink(missing_ok=True)
        with sessions() as session:
            ShipmentRepository(session).finish_photo(shipment_id, ready=True)
    except Exception as exc:
        # Never log exceptions from HTTP clients: they can contain signed URLs or credentials.
        logger.warning("CCTV photo unavailable for %s: %s", shipment_id, type(exc).__name__)
        if saved:
            destination.unlink(missing_ok=True)
        try:
            with sessions() as session:
                ShipmentRepository(session).finish_photo(shipment_id, ready=False)
        except Exception as update_exc:
            logger.error("Could not save CCTV failure status: %s", type(update_exc).__name__)
