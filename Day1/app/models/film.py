from datetime import datetime, timezone
from pydantic import BaseModel, Field


class Film(BaseModel):
    id: int
    title: str
    release_year: int
    genre: str
    description: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class FilmResponse(BaseModel):
    id: int
    title: str
    director: str
    release_year: int
    genre: str
    description: str
    created_at: datetime