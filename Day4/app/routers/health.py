from __future__ import annotations

from datetime import datetime, timezone
import logging
from fastapi import APIRouter, Depends
from app.core import project_config
from app.dependencies import DatabaseSession, get_db, get_request_id
from app.schemas.common import HealthResponse

logger = logging.getLogger("film_review.routers.health")

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse, summary="Service health check")
async def get_health(
    db: DatabaseSession = Depends(get_db),
    request_id: str = Depends(get_request_id),
) -> HealthResponse:
    """
    Check the health and availability of the service.
    Demonstrates dependency injection for system status, database connection test, and request ID.
    """
    logger.info(f"[{request_id}] Health check ok | API {project_config.API_VERSION} | DB active={db.is_active}")

    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc),
    )
