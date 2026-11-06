from datetime import datetime, timezone
import uuid
from pydantic import Field, computed_field, model_validator
from app.schemas.base import AppBaseModel


class ReviewBase(AppBaseModel):
    """Reusable base review model enforcing integer rating [1, 10] and min 50 chars."""

    film_id: uuid.UUID = Field(..., strict=False)
    rating: int = Field(..., ge=1, le=10)
    review: str = Field(..., min_length=50, max_length=5000)


class ReviewCreate(ReviewBase):
    """Creation model adding optional reviewer display name and user_id."""

    reviewer_display_name: str = Field(default="Anonymous Critic", min_length=2, max_length=50)
    user_id: uuid.UUID | None = Field(default=None, strict=False)


class ReviewUpdate(AppBaseModel):
    """Partial update model."""

    rating: int | None = Field(default=None, ge=1, le=10)
    review: str | None = Field(default=None, min_length=50)
    user_id: uuid.UUID | None = Field(default=None, strict=False, description="User ID requesting update for author validation")


class ReviewResponse(ReviewBase):
    """Response model extending ReviewBase with id and submission timestamp."""

    id: uuid.UUID = Field(..., strict=False)
    user_id: uuid.UUID | None = Field(default=None, strict=False)
    reviewer_display_name: str
    submitted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# Review domain entity aliases to ReviewResponse (eliminates duplicate model definition)
Review = ReviewResponse


class RatingRangeFilter(AppBaseModel):
    """Rating bounds demonstrating cross-field validation with @model_validator."""

    min_rating: int = Field(default=1, ge=1, le=10)
    max_rating: int = Field(default=10, ge=1, le=10)

    @model_validator(mode="after")
    def validate_rating_bounds(self) -> "RatingRangeFilter":
        if self.min_rating > self.max_rating:
            raise ValueError(f"min_rating ({self.min_rating}) cannot exceed max_rating ({self.max_rating})")
        return self


class ReviewFilterQuery(AppBaseModel):
    """
    Typed query schema for review listing, pagination, and multi-field filtering.
    Supports:
    - min_rating: minimum integer rating [1, 10]
    - max_rating: maximum integer rating [1, 10]
    - reviewer / username: filter by reviewer display name or user username
    - date_from / created_from: start date filter (inclusive)
    - date_to / created_to: end date filter (inclusive)
    - page: 1-indexed page number
    - page_size: items per page
    """

    page: int = Field(default=1, ge=1)
    limit: int = Field(default=10, ge=1, le=100, description="Maximum items per page")
    page_size: int | None = Field(default=None, ge=1, le=100, description="Alias for limit")
    min_rating: int | None = Field(default=None, ge=1, le=10)
    max_rating: int | None = Field(default=None, ge=1, le=10)
    reviewer: str | None = None
    username: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    created_from: datetime | None = None
    created_to: datetime | None = None

    @model_validator(mode="after")
    def validate_filters(self) -> "ReviewFilterQuery":
        # Standardize limit: if legacy page_size is provided, map to limit
        if self.page_size is not None:
            self.limit = self.page_size
        else:
            self.page_size = self.limit

        if self.min_rating is not None and self.max_rating is not None:
            if self.min_rating > self.max_rating:
                raise ValueError(
                    f"min_rating ({self.min_rating}) cannot be greater than max_rating ({self.max_rating})"
                )

        # Synchronize username with reviewer
        if self.username is None and self.reviewer is not None:
            self.username = self.reviewer
        elif self.reviewer is None and self.username is not None:
            self.reviewer = self.username

        # Synchronize date_from with created_from
        if self.date_from is None and self.created_from is not None:
            self.date_from = self.created_from
        elif self.created_from is None and self.date_from is not None:
            self.created_from = self.date_from

        # Synchronize date_to with created_to
        if self.date_to is None and self.created_to is not None:
            self.date_to = self.created_to
        elif self.created_to is None and self.date_to is not None:
            self.created_to = self.date_to

        if self.date_from is not None and self.date_to is not None:
            if self.date_from > self.date_to:
                raise ValueError("date_from cannot be greater than date_to")
        return self


class PaginatedReviewResponse(AppBaseModel):
    """Offset-based paginated response model for review listing."""

    page: int = Field(..., ge=1, description="Current page number")
    limit: int = Field(default=10, ge=1, description="Number of records per page")
    total: int = Field(..., ge=0, description="Total matching records across all pages")
    total_pages: int = Field(..., ge=0, description="Total calculated pages")
    total_records: int = Field(..., ge=0, description="Alias for total matching records")
    items: list[ReviewResponse] = Field(default_factory=list, description="Reviews belonging to requested page")
    reviews: list[ReviewResponse] = Field(default_factory=list, description="Reviews alias for items")

    @computed_field
    @property
    def page_size(self) -> int:
        """Alias for limit to maintain backward compatibility."""
        return self.limit
