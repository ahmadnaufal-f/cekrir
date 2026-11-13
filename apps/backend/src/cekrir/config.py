from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, HttpUrl, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CEKRIR_",
        env_file=(Path(__file__).resolve().parents[4] / ".env", ".env"),
        extra="ignore",
        populate_by_name=True,
    )

    database_url: str = Field(
        default="postgresql://cekrir:cekrir@127.0.0.1:5432/cekrir",
        validation_alias="DATABASE_URL",
    )
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
        if not value.startswith(("postgresql://", "postgres://")):
            raise ValueError("DATABASE_URL must be a PostgreSQL connection URL")
        return value

    @model_validator(mode="after")
    def validate_provider(self) -> "Settings":
        if self.tracking_provider == "http" and self.tracking_api_url is None:
            raise ValueError("CEKRIR_TRACKING_API_URL is required for the http provider")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
