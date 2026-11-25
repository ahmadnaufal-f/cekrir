from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints, field_validator


class CourierInput(BaseModel):
    courier: str = Field(min_length=2, max_length=32, pattern=r"^[a-z0-9_-]+$")

    @field_validator("courier", mode="before")
    @classmethod
    def normalize_courier(cls, value: object) -> object:
        return value.strip().lower() if isinstance(value, str) else value


class ResiInput(CourierInput):
    resi_number: str = Field(min_length=3, max_length=64, pattern=r"^[A-Za-z0-9-]+$")

    @field_validator("resi_number", mode="before")
    @classmethod
    def normalize_resi(cls, value: object) -> object:
        return value.strip().upper() if isinstance(value, str) else value


class DetectionInput(ResiInput):
    camera_id: str = Field(min_length=1, max_length=100)


class ExpectedPackageInput(ResiInput):
    courier: Literal["spx"]
    sender_name: Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)] | None = (
        None
    )
    product_names: list[
        Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
    ] = Field(default_factory=list, max_length=20)


class CameraFrameInput(CourierInput):
    camera_id: str = Field(min_length=1, max_length=100)
