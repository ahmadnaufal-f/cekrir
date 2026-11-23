from urllib.parse import urlsplit
from uuid import UUID

from pydantic import BaseModel, Field, SecretStr, field_validator


class CctvCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    stream_url: str = Field(min_length=1, max_length=2048)
    username: SecretStr = Field(min_length=1, max_length=512)
    password: SecretStr = Field(min_length=1, max_length=1024)

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("stream_url")
    @classmethod
    def valid_stream_url(cls, value: str) -> str:
        try:
            parsed = urlsplit(value)
            if (
                parsed.scheme not in {"rtsp", "rtmp", "rtmps"}
                or not parsed.hostname
                or parsed.username is not None
                or parsed.password is not None
            ):
                raise ValueError
            _ = parsed.port
        except ValueError as exc:
            raise ValueError(
                "Use a valid RTSP, RTMP, or RTMPS URL without embedded credentials"
            ) from exc
        return value


class FcmRegistration(BaseModel):
    token: SecretStr = Field(min_length=1, max_length=4096)
    location_id: UUID


class FcmUnregister(BaseModel):
    token: SecretStr = Field(min_length=1, max_length=4096)
