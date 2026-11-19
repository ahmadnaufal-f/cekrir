import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class CredentialsInput(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=256)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: object) -> object:
        if isinstance(value, str):
            normalized = value.strip().lower()
            if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", normalized):
                raise ValueError("Enter a valid email address")
            return normalized
        return value


class RegisterInput(CredentialsInput):
    full_name: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=12, max_length=72)

    @field_validator("full_name", mode="before")
    @classmethod
    def strip_full_name(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("password")
    @classmethod
    def password_is_at_most_72_bytes(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must be no more than 72 UTF-8 bytes")
        return value


class RefreshInput(BaseModel):
    refresh_token: str = Field(min_length=1)


class VerificationInput(BaseModel):
    token: str = Field(pattern=r"^[A-Za-z0-9_-]{43}$")


class RoleUpdate(BaseModel):
    role: Literal["admin", "member"]
