from datetime import datetime, timezone
from pydantic import Field, computed_field, field_validator, model_validator
from app.models.base import AppBaseModel


class FilmBase(AppBaseModel):
    """Reusable base film model with common attributes."""

    title: str = Field(..., min_length=1, max_length=200)
    release_year: int = Field(..., ge=1888, le=2100, alias="releaseYear")
    genre: str = Field(..., min_length=2, max_length=50)
    director: str = Field(..., min_length=2, max_length=100)
    description: str = Field(default="", max_length=2000)

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        if not any(c.isalnum() for c in v):
            raise ValueError("Film title must contain at least one alphanumeric character")
        return v

    @field_validator("release_year")
    @classmethod
    def validate_release_year(cls, v: int) -> int:
        max_year = datetime.now(timezone.utc).year + 5
        if v > max_year:
            raise ValueError(f"Release year cannot be more than 5 years in the future (max: {max_year})")
        return v


class FilmCreate(FilmBase):
    """Creation model — inherits all fields directly from FilmBase."""
    pass


class FilmUpdate(AppBaseModel):
    """Partial update model with optional fields."""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    release_year: int | None = Field(default=None, ge=1888, le=2100, alias="releaseYear")
    genre: str | None = Field(default=None, min_length=2, max_length=50)
    director: str | None = Field(default=None, min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=2000)


class FilmResponse(FilmBase):
    """Response model extending FilmBase with ID and computed years_since_release."""

    id: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @computed_field
    @property
    def years_since_release(self) -> int:
        return max(0, datetime.now(timezone.utc).year - self.release_year)


# Film domain entity aliases to FilmResponse (eliminates duplicate model definition)
Film = FilmResponse


class FilmFilterQuery(AppBaseModel):
    """Filter parameters demonstrating @model_validator relationship validation."""

    genre: str | None = None
    start_year: int | None = Field(default=None, ge=1888, le=2100)
    end_year: int | None = Field(default=None, ge=1888, le=2100)
    limit: int = Field(default=10, ge=1, le=100)

    @model_validator(mode="after")
    def validate_year_range(self) -> "FilmFilterQuery":
        if self.start_year is not None and self.end_year is not None:
            if self.start_year > self.end_year:
                raise ValueError(
                    f"start_year ({self.start_year}) cannot be greater than end_year ({self.end_year})"
                )
        return self 