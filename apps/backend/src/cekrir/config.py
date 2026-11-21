from functools import lru_cache
from pathlib import Path
from secrets import token_urlsafe
from typing import Literal

from pydantic import Field, HttpUrl, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CEKRIR_",
        env_file=(
            Path(__file__).resolve().parents[4] / ".env",
            Path(__file__).resolve().parents[2] / ".env",
        ),
        extra="ignore",
        populate_by_name=True,
    )

    database_url: str = Field(
        default="postgresql://cekrir:cekrir@127.0.0.1:5432/cekrir",
        validation_alias="DATABASE_URL",
    )
    redis_url: str = "redis://127.0.0.1:6379/0"
    jwt_secret_key: SecretStr = Field(default_factory=lambda: SecretStr(token_urlsafe(48)))
    jwt_issuer: str = "cekrir-api"
    bootstrap_admin_email: str | None = None
    bootstrap_admin_full_name: str = Field(default="Administrator", min_length=1, max_length=200)
    bootstrap_admin_password: SecretStr | None = None
    email_provider: Literal["smtp", "resend"] = "smtp"
    resend_api_key: SecretStr | None = None
    resend_from: str | None = None
    smtp_host: str | None = None
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_security: Literal["starttls", "ssl", "plain"] = "starttls"
    smtp_username: str | None = None
    smtp_password: SecretStr | None = None
    smtp_from: str | None = None
    verification_url: HttpUrl | None = None
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "capacitor://localhost",
        "http://localhost",
        "https://localhost",
    ]
    tracking_provider: Literal["demo", "http"] = "demo"
    tracking_api_url: HttpUrl | None = None
    tracking_api_key: SecretStr | None = None
    ingest_api_key: SecretStr | None = None

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        if not value.startswith(("postgresql://", "postgres://", "postgresql+psycopg://")):
            raise ValueError("DATABASE_URL must be a PostgreSQL connection URL")
        return value

    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt_secret_key(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value()) < 32:
            raise ValueError("CEKRIR_JWT_SECRET_KEY must contain at least 32 characters")
        return value

    @field_validator("bootstrap_admin_full_name", mode="before")
    @classmethod
    def normalize_bootstrap_admin_full_name(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_provider(self) -> "Settings":
        if self.tracking_provider == "http" and self.tracking_api_url is None:
            raise ValueError("CEKRIR_TRACKING_API_URL is required for the http provider")
        if bool(self.bootstrap_admin_email) != bool(self.bootstrap_admin_password):
            raise ValueError(
                "CEKRIR_BOOTSTRAP_ADMIN_EMAIL and CEKRIR_BOOTSTRAP_ADMIN_PASSWORD "
                "must be configured together"
            )
        if bool(self.smtp_username) != bool(self.smtp_password):
            raise ValueError("CEKRIR_SMTP_USERNAME and CEKRIR_SMTP_PASSWORD must be set together")
        return self

    @field_validator("bootstrap_admin_password")
    @classmethod
    def validate_bootstrap_admin_password(cls, value: SecretStr | None) -> SecretStr | None:
        if value is not None:
            password = value.get_secret_value()
            if len(password) < 12 or len(password.encode("utf-8")) > 72:
                raise ValueError("Bootstrap admin password must be 12 to 72 UTF-8 bytes")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
