from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from cekrir.db.model.base import Base


class LocationMember(Base):
    __tablename__ = "location_members"
    __table_args__ = (Index("location_members_user_id_idx", "user_id"),)

    location_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("locations.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("cekrir_user.id", ondelete="CASCADE"), primary_key=True
    )


class CameraDevice(Base):
    __tablename__ = "camera_devices"
    __table_args__ = (Index("camera_devices_location_id_idx", "location_id"),)

    camera_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    location_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("locations.id", ondelete="CASCADE"), nullable=False
    )


class EspDevice(Base):
    __tablename__ = "esp_devices"

    device_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    location_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("locations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    credential_hash: Mapped[str | None] = mapped_column(String(64))
    last_seen_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True, precision=3))


class CctvCamera(Base):
    __tablename__ = "cctv_cameras"
    __table_args__ = (Index("ix_cctv_cameras_location_id", "location_id"),)
    id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    location_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("locations.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    stream_url_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    username_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    password_encrypted: Mapped[str] = mapped_column(Text, nullable=False)


class FcmDevice(Base):
    __tablename__ = "fcm_devices"
    __table_args__ = (Index("ix_fcm_devices_user_id", "user_id"),)
    id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("cekrir_user.id", ondelete="CASCADE"),
        nullable=False,
    )
    token: Mapped[str] = mapped_column(Text, nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)


class FcmDeviceLocation(Base):
    __tablename__ = "fcm_device_locations"
    device_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("fcm_devices.id", ondelete="CASCADE"), primary_key=True
    )
    location_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("locations.id", ondelete="CASCADE"), primary_key=True
    )
