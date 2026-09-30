from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str

    # Security & Tokens
    TOKEN_SECRET_KEY: str = Field(..., min_length=16)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    ALLOWED_CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8000"]

    # App Metadata
    API_VERSION: str = "3.0.0"
    PROJECT_NAME: str = "Film Review Platform API"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    model_config = SettingsConfigDict(
        env_file=(str(_ENV_PATH), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("ALLOWED_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            return json.loads(v) if v.strip().startswith("[") else [x.strip() for x in v.split(",") if x.strip()]
        return v

    @property
    def ACCESS_TOKEN_EXPIRY_DURATION(self) -> int:
        return self.ACCESS_TOKEN_EXPIRE_MINUTES

    @property
    def REFRESH_TOKEN_EXPIRY_DURATION(self) -> int:
        return self.REFRESH_TOKEN_EXPIRE_DAYS

    @property
    def VERSION(self) -> str:
        return self.API_VERSION


settings = Settings()
