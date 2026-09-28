from datetime import datetime, timezone
from fastapi import APIRouter
from app.schemas.common import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse, summary="Service health check")
def get_health() -> HealthResponse:
    """
    Check the health and availability of the service.
    Returns status and current UTC server timestamp.
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc),
    )
