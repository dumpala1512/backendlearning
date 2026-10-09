from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    """
    Dynamic environment settings loaded exclusively from environment variables / .env.
    All static project metadata and constants are defined in project_config.py.
    """
    # Database
    DATABASE_URL: str

    # Security & Tokens
    TOKEN_SECRET_KEY: str = Field(..., min_length=16)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Redis Configuration
    REDIS_URL: str | None = None
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str | None = None
    REDIS_DB: int = 0
    CACHE_TTL_SECONDS: int = 300
    CACHE_TTL: int = 300  # Alias for CACHE_TTL_SECONDS

    # Logging
    LOG_LEVEL: str = "INFO"

    @property
    def refresh_token_ttl_seconds(self) -> int:
        """Derived refresh token TTL in seconds matching JWT expiration."""
        return self.REFRESH_TOKEN_EXPIRE_DAYS * 86400

    @property
    def redis_connection_url(self) -> str:
        """Construct full Redis connection URL from components if REDIS_URL is not set."""
        if self.REDIS_URL:
            return self.REDIS_URL
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    model_config = SettingsConfigDict(
        env_file=(str(_ENV_PATH), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
