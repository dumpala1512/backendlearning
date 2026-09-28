from datetime import datetime, timezone
from pydantic import Field, model_validator
from app.models.base import AppBaseModel


class ReviewBase(AppBaseModel):
    """Reusable base review model enforcing integer rating [1, 10] and min 50 chars."""

    film_id: int = Field(..., ge=1)
    rating: int = Field(..., ge=1, le=10)
    review: str = Field(..., min_length=50, max_length=5000)


class ReviewCreate(ReviewBase):
    """Creation model adding optional reviewer display name."""

    reviewer_display_name: str = Field(default="Anonymous Critic", min_length=2, max_length=50)


class ReviewUpdate(AppBaseModel):
    """Partial update model."""

    rating: int | None = Field(default=None, ge=1, le=10)
    review: str | None = Field(default=None, min_length=50)


class ReviewResponse(ReviewBase):
    """Response model extending ReviewBase with id and submission timestamp."""

    id: int
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
