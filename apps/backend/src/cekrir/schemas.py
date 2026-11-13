from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

ShipmentStatus = Literal["pending", "in_transit", "delivered", "exception"]


class ResiInput(BaseModel):
    resi_number: str = Field(min_length=3, max_length=64, pattern=r"^[A-Za-z0-9-]+$")
    courier: str = Field(min_length=2, max_length=32, pattern=r"^[a-z0-9_-]+$")

    @field_validator("resi_number", mode="before")
    @classmethod
    def normalize_resi(cls, value: object) -> object:
        return value.strip().upper() if isinstance(value, str) else value

    @field_validator("courier", mode="before")
    @classmethod
    def normalize_courier(cls, value: object) -> object:
        return value.strip().lower() if isinstance(value, str) else value


class DetectionInput(ResiInput):
    camera_id: str = Field(min_length=1, max_length=100)


class TrackingEvent(BaseModel):
    occurred_at: datetime
    description: str = Field(min_length=1, max_length=1000)
    location: str | None = Field(default=None, max_length=200)


class TrackingSnapshot(BaseModel):
    status: ShipmentStatus
    summary: str = Field(min_length=1, max_length=1000)
    history: list[TrackingEvent] = Field(default_factory=list, max_length=100)


class ShipmentRead(TrackingSnapshot):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    resi_number: str
    courier: str
    source: Literal["manual", "camera"]
    camera_id: str | None
    provider: str
    created_at: datetime
    checked_at: datetime
    last_detected_at: datetime | None


class DetectionResult(BaseModel):
    created: bool
    shipment: ShipmentRead


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    shipment_id: UUID
    title: str
    message: str
    created_at: datetime
