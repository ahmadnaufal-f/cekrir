from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from sqlalchemy import JSON, Column, UniqueConstraint
from sqlmodel import Field, SQLModel

ShipmentStatus = Literal["pending", "in_transit", "delivered", "exception"]


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


class Shipment(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("courier", "resi_number"),)

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    resi_number: str = Field(index=True)
    courier: str
    source: str
    camera_id: str | None = None
    status: str = "pending"
    summary: str = "Awaiting tracking information"
    provider: str = "demo"
    history: list[dict[str, str]] = Field(default_factory=list, sa_column=Column(JSON))
    created_at: str = Field(default_factory=utc_now)
    checked_at: str = Field(default_factory=utc_now)
    last_detected_at: str | None = None


class Notification(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    shipment_id: str = Field(foreign_key="shipment.id", index=True)
    title: str
    message: str
    created_at: str = Field(default_factory=utc_now)
