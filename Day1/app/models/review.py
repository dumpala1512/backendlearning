from datetime import datetime, timezone
from pydantic import BaseModel, Field


class Review(BaseModel):
    id: int
    film_id: int
    user_id: int
    rating: int
    comment: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
