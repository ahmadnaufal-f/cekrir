from functools import lru_cache
from typing import Literal

from pydantic import HttpUrl, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CEKRIR_", env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./data/cekrir.db"
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

    @model_validator(mode="after")
    def validate_provider(self) -> "Settings":
        if self.tracking_provider == "http" and self.tracking_api_url is None:
            raise ValueError("CEKRIR_TRACKING_API_URL is required for the http provider")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
