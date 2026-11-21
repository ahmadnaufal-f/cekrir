from uuid import UUID

from sqlalchemy import ForeignKey, Index, String
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
