from datetime import datetime, timezone
import logging
from fastapi import APIRouter, Depends, Response
from app.core.config import Settings
from app.dependencies import DatabaseSession, get_db, get_settings, get_trace_id
from app.models.common import HealthResponse

logger = logging.getLogger("film_review.routers.health")

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse, summary="Service health check")
def get_health(
    response: Response,
    settings: Settings = Depends(get_settings),
    db: DatabaseSession = Depends(get_db),
    trace_id: str = Depends(get_trace_id),
) -> HealthResponse:
    """
    Check the health and availability of the service.
    Demonstrates dependency injection for system status, database connection test, and trace ID.
    """
    response.headers["X-Trace-Id"] = trace_id

    logger.info(f"[{trace_id}] Health check ok | API {settings.API_VERSION} | DB active={db.is_active}")

    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc),
    )
