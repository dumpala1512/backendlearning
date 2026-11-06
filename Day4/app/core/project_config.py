"""
Static project constants and application metadata.
"""
from __future__ import annotations

# Static Project Metadata
PROJECT_NAME: str = "Film Review Platform API"
API_VERSION: str = "5.0.0"
API_V1_PREFIX: str = "/api/v1"
ENVIRONMENT: str = "development"
DEBUG: bool = False

# Static CORS Configuration
ALLOWED_CORS_ORIGINS: list[str] = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
CORS_ALLOWED_METHODS: list[str] = [
    "GET",
    "POST",
    "PUT",
    "PATCH",
    "DELETE",
    "OPTIONS",
]
CORS_ALLOWED_HEADERS: list[str] = [
    "Content-Type",
    "Authorization",
    "X-Request-ID",
    "Accept",
]
CORS_EXPOSE_HEADERS: list[str] = [
    "X-Request-ID",
    "X-Process-Time",
]
