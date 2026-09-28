from datetime import datetime
from pydantic import BaseModel, Field


class MessageResponse(BaseModel):
    message: str
    success: bool = True


class HealthResponse(BaseModel):
    status: str = "ok"
    timestamp: datetime = Field(description="Current server UTC timestamp")
