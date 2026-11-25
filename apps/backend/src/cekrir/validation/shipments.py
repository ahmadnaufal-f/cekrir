from pydantic import BaseModel, Field, field_validator


class CourierInput(BaseModel):
    courier: str = Field(min_length=2, max_length=32, pattern=r"^[a-z0-9_-]+$")

    @field_validator("courier", mode="before")
    @classmethod
    def normalize_courier(cls, value: object) -> object:
        return value.strip().lower() if isinstance(value, str) else value


class ResiNumberInput(BaseModel):
    resi_number: str = Field(min_length=3, max_length=64, pattern=r"^[A-Za-z0-9-]+$")

    @field_validator("resi_number", mode="before")
    @classmethod
    def normalize_resi(cls, value: object) -> object:
        return value.strip().upper() if isinstance(value, str) else value


class ResiInput(ResiNumberInput, CourierInput):
    pass


class DetectionInput(ResiInput):
    camera_id: str = Field(min_length=1, max_length=100)


class CameraCourierInput(CourierInput):
    courier: str | None = Field(default=None, min_length=2, max_length=32, pattern=r"^[a-z0-9_-]+$")

    @field_validator("courier", mode="before")
    @classmethod
    def empty_courier_is_none(cls, value: object) -> object:
        return None if isinstance(value, str) and not value.strip() else value


class CameraFrameInput(CameraCourierInput):
    camera_id: str = Field(min_length=1, max_length=100)
