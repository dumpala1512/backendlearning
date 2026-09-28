from datetime import datetime
from pydantic import BaseModel, Field


class FilmCreate(BaseModel):
    title: str = Field(..., min_length=1, examples=["Inception"])
    director: str = Field(..., min_length=1, examples=["Christopher Nolan"])
    release_year: int = Field(..., ge=1888, le=2100, examples=[2010])
    genre: str = Field(..., min_length=1, examples=["Sci-Fi"])
    description: str = Field("", examples=["A thief who steals corporate secrets through dream-sharing technology."])


class FilmUpdate(BaseModel):
    title: str | None = Field(None, examples=["Inception (Remastered)"])
    director: str | None = Field(None, examples=["Christopher Nolan"])
    release_year: int | None = Field(None, ge=1888, le=2100, examples=[2010])
    genre: str | None = Field(None, examples=["Sci-Fi / Thriller"])
    description: str | None = Field(None, examples=["Updated description."])


class FilmResponse(BaseModel):
    id: int
    title: str
    director: str
    release_year: int
    genre: str
    description: str
    created_at: datetime
