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
    "http://localhost:8000",
]
