from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, Index, String, Text, text
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cekrir.db.model.base import Base

if TYPE_CHECKING:
    from cekrir.db.model.notification import Notification


class ShipmentStatus(StrEnum):
    PENDING = "pending"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    EXCEPTION = "exception"


class ShipmentSource(StrEnum):
    MANUAL = "manual"
    CAMERA = "camera"


class Shipment(Base):
    __tablename__ = "shipment"
    __table_args__ = (
        Index("shipment_resi_number_idx", "resi_number"),
        Index("shipment_created_at_id_idx", text("created_at DESC"), text("id DESC")),
        Index("shipment_courier_resi_number_key", "courier", "resi_number", unique=True),
        CheckConstraint(
            "photo_status IN ('not_requested', 'pending', 'ready', 'unavailable')",
            name="shipment_photo_status_check",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    resi_number: Mapped[str] = mapped_column(String(64), nullable=False)
    courier: Mapped[str] = mapped_column(String(32), nullable=False)
    source: Mapped[ShipmentSource] = mapped_column(
        SqlEnum(
            ShipmentSource,
            name="ShipmentSource",
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
    )
    camera_id: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[ShipmentStatus] = mapped_column(
        SqlEnum(
            ShipmentStatus,
            name="ShipmentStatus",
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
        server_default=text("'pending'::\"ShipmentStatus\""),
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    history: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True, precision=3),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    checked_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True, precision=3),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    last_detected_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True, precision=3))
    photo_status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'not_requested'")
    )
    photo_captured_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True, precision=3)
    )
    notifications: Mapped[list[Notification]] = relationship(
        "Notification", back_populates="shipment", cascade="all, delete-orphan"
    )
