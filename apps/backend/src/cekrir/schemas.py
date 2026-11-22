from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

ShipmentStatus = Literal["pending", "in_transit", "delivered", "exception"]


class LocationRead(BaseModel):
    id: UUID
    name: str
    esp_device_id: str | None
    onboarding_complete: bool
    camera_ids: list[str]


class FrameDetection(BaseModel):
    resi_number: str
    shipment_id: UUID
    created: bool


class CameraFrameResult(BaseModel):
    detected_count: int = 0
    ambiguous: bool = False
    detections: list[FrameDetection] = Field(default_factory=list)


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


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    full_name: str
    role: Literal["admin", "member"]
    is_active: bool
    created_at: datetime


class TokenRead(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
    refresh_expires_in: int
    user: UserRead
    location_id: UUID | None = None
    esp_device_id: str | None = None


class VerificationPending(BaseModel):
    detail: str = "Check your email for a verification link."


class RegistrationPending(VerificationPending):
    location_id: UUID | None = None
    esp_device_id: str | None = None


class PaymentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    reference: str
    amount: int
    currency: Literal["IDR"]
    status: Literal["draft"]
    created_at: datetime
