from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.secrets import load_application_credentials

logger = logging.getLogger("film_review.core.config")

# Resolve absolute path to .env file relative to project root
_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    """
    Application Settings
    ====================
    Separates non-sensitive environment configuration from sensitive credentials.

    Architecture Principles:
    - All non-sensitive configuration is declared as required BaseSettings fields
      and loaded exclusively from environment variables or the .env file.
    - No environment-specific defaults (localhost, ports, usernames, database names)
      are hardcoded in this source code.
    - Sensitive credentials are loaded from AWS Secrets Manager at application startup.
      Local fallback credentials and developer seed passwords are read from environment
      variables or the ignored .env file.
    - DATABASE_URL is constructed dynamically in load_secrets() using the verified
      credentials and cannot be supplied via .env.
    - Startup fails immediately with clear errors if required configuration or
      secrets are missing or unreachable.
    """

    # --------------------------------------------------------------------------
    # 1. Non-Sensitive Configuration (Loaded from .env / environment variables)
    # --------------------------------------------------------------------------

    # AWS Secrets Manager Configuration
    AWS_REGION: str
    AWS_SECRETS_NAME: str
    AWS_ENDPOINT_URL: str | None = None

    # S3 / Storage Configuration
    S3_BUCKET_NAME: str | None = None
    S3_ENDPOINT_URL: str | None = None
    S3_PRESIGNED_ENDPOINT_URL: str | None = None
    S3_CORS_ALLOWED_ORIGINS: str | None = None
    AWS_ACCESS_KEY_ID: str | None = None
    AWS_SECRET_ACCESS_KEY: str | None = None
    AWS_SESSION_TOKEN: str | None = None
    AWS_ENDPOINT_URL_DOCKER: str | None = None
    S3_SIGNATURE_VERSION: str | None = "s3v4"
    PRESIGNED_URL_EXPIRE_SECONDS: int = 3600
    S3_MAX_FILE_SIZE_BYTES: int | None = None
    S3_ALLOWED_MIME_TYPES: str | None = None

    # Database Non-Sensitive Configuration
    DB_HOST: str
    DB_PORT: int
    DB_USER: str
    DB_NAME: str
    DB_DRIVER: str

    # Redis Non-Sensitive Configuration
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_DB: int
    REDIS_URL: str | None = None
    REDIS_PASSWORD: str | None = None

    # Event publishing / queue configuration
    EVENT_QUEUE_URL: str | None = None
    QUEUE_URL: str | None = None
    EVENT_PUBLISHER_ENABLED: bool = True
    EVENT_PUBLISHER_MODE: str = "local"

    # Security & Tokens (Non-sensitive expiration settings)
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_DAYS: int

    # Caching & Logging
    CACHE_TTL_SECONDS: int
    LOG_LEVEL: str

    # --------------------------------------------------------------------------
    # 2. Sensitive Credentials (Loaded exclusively from AWS Secrets Manager)
    #    Declared as Optional (None) until load_secrets() populates them.
    # --------------------------------------------------------------------------
    DB_PASSWORD: str | None = None
    JWT_SECRET_KEY: str | None = None
    NOTIFICATION_API_KEY: str | None = None
    DATABASE_URL: str | None = None
    POSTGRES_PASSWORD: str | None = None
    LOCAL_TOKEN_SECRET_KEY: str | None = None
    LOCAL_NOTIFICATION_API_KEY: str | None = None
    SEED_ADMIN_PASSWORD: str | None = None
    SEED_MARCUS_CRITIC_PASSWORD: str | None = None
    SEED_ELENA_VIEWER_PASSWORD: str | None = None
    SEED_ALEX_VIEWER_PASSWORD: str | None = None
    SEED_BOB_CRITIC_PASSWORD: str | None = None

    # --------------------------------------------------------------------------
    # 3. Derived Properties & Backward-Compatible Accessors
    # --------------------------------------------------------------------------

    @property
    def TOKEN_SECRET_KEY(self) -> str:
        """
        Backward-compatible accessor for JWT_SECRET_KEY.
        Eliminates duplicate state while preserving existing callers.
        """
        if self.JWT_SECRET_KEY is None:
            raise ValueError("JWT_SECRET_KEY has not been loaded from AWS Secrets Manager.")
        return self.JWT_SECRET_KEY

    @property
    def CACHE_TTL(self) -> int:
        """Backward-compatible alias for CACHE_TTL_SECONDS."""
        return self.CACHE_TTL_SECONDS

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

    @property
    def event_queue_url(self) -> str | None:
        """Return the configured queue URL, preferring the dedicated event publisher setting."""
        return self.EVENT_QUEUE_URL or self.QUEUE_URL

    @property
    def s3_endpoint_url(self) -> str | None:
        """Return the configured S3 endpoint URL for LocalStack/Floci compatibility."""
        return self.S3_ENDPOINT_URL or self.AWS_ENDPOINT_URL

    model_config = SettingsConfigDict(
        env_file=(str(_ENV_PATH), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --------------------------------------------------------------------------
    # 4. Lifecycle Initialization (Pydantic v2 post-init hook)
    # --------------------------------------------------------------------------

    def model_post_init(self, __context: Any) -> None:
        """
        Post-initialization lifecycle hook.
        Order of operations:
        1. Validate configuration loaded from environment variables / .env.
        2. Fetch sensitive credentials from AWS Secrets Manager.
        3. Dynamically construct runtime settings (such as DATABASE_URL).
        """
        super().model_post_init(__context)
        self.load_secrets()

    def load_secrets(self) -> None:
        """
        Retrieve sensitive credentials exclusively from AWS Secrets Manager.
        Builds DATABASE_URL dynamically using the retrieved DB password.
        Uses local-only credentials from environment configuration when the AWS
        endpoint is unavailable during offline or test execution.
        """
        try:
            credentials = load_application_credentials(
                secret_name=self.AWS_SECRETS_NAME,
                region_name=self.AWS_REGION,
                endpoint_url=self.AWS_ENDPOINT_URL,
            )
        except Exception as exc:
            logger.warning(
                "AWS Secrets Manager unavailable at startup; using local-safe defaults. "
                "Startup validation in lifespan will still enforce connectivity when app is launched. "
                "Original error: %s",
                exc,
            )
            if not self.POSTGRES_PASSWORD or not self.LOCAL_TOKEN_SECRET_KEY:
                raise RuntimeError(
                    "AWS Secrets Manager is unavailable and local credentials are not configured. "
                    "Set POSTGRES_PASSWORD and LOCAL_TOKEN_SECRET_KEY in the environment."
                ) from exc
            self.DB_PASSWORD = self.POSTGRES_PASSWORD
            self.JWT_SECRET_KEY = self.LOCAL_TOKEN_SECRET_KEY
            self.NOTIFICATION_API_KEY = self.LOCAL_NOTIFICATION_API_KEY
            self.DATABASE_URL = (
                f"{self.DB_DRIVER}://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            )
            return

        # Populate runtime secrets
        self.DB_PASSWORD = credentials["database_password"]
        self.JWT_SECRET_KEY = credentials.get("jwt_secret_key") or credentials["token_secret_key"]
        self.NOTIFICATION_API_KEY = credentials.get("notification_api_key")

        # Dynamically build DATABASE_URL using non-sensitive config and secret password
        self.DATABASE_URL = (
            f"{self.DB_DRIVER}://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )


# Singleton application settings instance
settings = Settings()
