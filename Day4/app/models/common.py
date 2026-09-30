from datetime import datetime
from app.models.base import AppBaseModel


class MessageResponse(AppBaseModel):
    """Generic message response."""

    message: str
    success: bool = True


class HealthResponse(AppBaseModel):
    """Health check response."""

    status: str = "healthy"
    timestamp: datetime
