import uuid
from datetime import datetime, timezone
from pydantic import Field, computed_field, field_validator, model_validator
from app.schemas.base import AppBaseModel


class FilmBase(AppBaseModel):
    """Reusable base film model with common attributes."""

    title: str = Field(..., min_length=1, max_length=200)
    release_year: int = Field(..., ge=1888, le=2031, alias="releaseYear")
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

    id: uuid.UUID = Field(..., strict=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    total_reviews: int = Field(default=0, ge=0)
    average_rating: float | None = Field(default=None)

    @computed_field
    @property
    def review_count(self) -> int:
        return self.total_reviews

    @computed_field
    @property
    def years_since_release(self) -> int:
        return max(0, datetime.now(timezone.utc).year - self.release_year)


# Film domain entity aliases to FilmResponse (eliminates duplicate model definition)
Film = FilmResponse


class FilmFilterQuery(AppBaseModel):
    """
    Typed query schema for film listing, pagination, and multi-field filtering.
    Standardized on 'limit' across both offset and cursor pagination.
    Supports:
    - genre: exact match
    - year_from: minimum release year
    - year_to: maximum release year
    - director: case-insensitive substring
    - page: 1-indexed page number
    - limit: maximum items per page
    - page_size: optional alias for limit (for backward compatibility)
    - cursor: opaque cursor token for cursor-based pagination
    """

    genre: str | None = None
    year_from: int | None = Field(default=None, ge=1888, le=2100)
    year_to: int | None = Field(default=None, ge=1888, le=2100)
    director: str | None = None
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=10, ge=1, le=100, description="Maximum items per page")
    page_size: int | None = Field(default=None, ge=1, le=100, description="Alias for limit")
    cursor: str | None = None

    @model_validator(mode="after")
    def validate_filters(self) -> "FilmFilterQuery":
        # Standardize limit: if legacy page_size is provided, map to limit
        if self.page_size is not None:
            self.limit = self.page_size
        else:
            self.page_size = self.limit

        if self.year_from is not None and self.year_to is not None:
            if self.year_from > self.year_to:
                raise ValueError(
                    f"year_from ({self.year_from}) cannot be greater than year_to ({self.year_to})"
                )
        return self


class PaginatedFilmResponse(AppBaseModel):
    """Offset-based paginated response model for film listing."""

    page: int = Field(..., ge=1, description="Current page number")
    limit: int = Field(default=10, ge=1, description="Number of records per page")
    total: int = Field(..., ge=0, description="Total matching records across all pages")
    total_pages: int = Field(..., ge=0, description="Total calculated pages")
    total_records: int = Field(..., ge=0, description="Alias for total matching records")
    items: list[FilmResponse] = Field(default_factory=list, description="Films belonging to requested page")

    @computed_field
    @property
    def page_size(self) -> int:
        """Alias for limit to maintain backward compatibility."""
        return self.limit


class CursorFilmResponse(AppBaseModel):
    """Cursor-based paginated response model for film listing."""

    items: list[FilmResponse] = Field(default_factory=list, description="Films for the current cursor page")
    next_cursor: str | None = Field(default=None, description="Opaque cursor token for the next page, or null if end of dataset")
    limit: int = Field(default=10, description="Maximum items per page") 