from __future__ import annotations

from typing import Any
import uuid
from fastapi import status

from app.exceptions.base import (
    DomainError,
    DuplicateEntityError,
    EntityNotFoundError,
    PermissionDeniedError,
    ValidationError,
)


class ReviewNotFoundError(EntityNotFoundError):
    """Raised when a specific Review cannot be found (HTTP 404)."""

    status_code: int = status.HTTP_404_NOT_FOUND
    default_message: str = "Review not found."

    def __init__(
        self,
        review_id: uuid.UUID | str,
        message: str | None = None,
        detail: dict[str, Any] | None = None,
        status_code: int | None = None,
    ) -> None:
        self.review_id = review_id
        super().__init__(
            message=message or f"Review with id {review_id} not found.",
            detail={"review_id": str(review_id), **(detail or {})},
            status_code=status_code,
        )


class ReviewAlreadyExistsError(DuplicateEntityError):
    """
    Raised when a user attempts to submit a second review for the same film (HTTP 409).
    Domain Rule 1: A user may submit only one review per film.
    """

    status_code: int = status.HTTP_409_CONFLICT
    default_message: str = "A user may submit only one review per film."

    def __init__(
        self,
        film_id: uuid.UUID | str,
        user_id: uuid.UUID | str,
        review_id: uuid.UUID | str | None = None,
        message: str | None = None,
        detail: dict[str, Any] | None = None,
        status_code: int | None = None,
    ) -> None:
        self.film_id = film_id
        self.user_id = user_id
        self.review_id = review_id
        details: dict[str, Any] = {
            "film_id": str(film_id),
            "user_id": str(user_id),
        }
        if review_id:
            details["review_id"] = str(review_id)
        details.update(detail or {})
        super().__init__(
            message=message
            or f"User {user_id} has already reviewed film {film_id} (Domain Rule 1: one review per user per film).",
            detail=details,
            status_code=status_code,
        )


class ReviewPermissionDeniedError(PermissionDeniedError):
    """
    Raised when a user attempts to update a review they did not author (HTTP 403).
    Domain Rule 2: Only the original author may update review rating and review body.
    """

    status_code: int = status.HTTP_403_FORBIDDEN
    default_message: str = "Only the original author may update review rating and review body."

    def __init__(
        self,
        review_id: uuid.UUID | str,
        user_id: uuid.UUID | str | None = None,
        message: str | None = None,
        detail: dict[str, Any] | None = None,
        status_code: int | None = None,
    ) -> None:
        self.review_id = review_id
        self.user_id = user_id
        user_suffix = f" by user {user_id}" if user_id else ""
        details: dict[str, Any] = {"review_id": str(review_id)}
        if user_id:
            details["user_id"] = str(user_id)
        details.update(detail or {})
        super().__init__(
            message=message
            or f"Permission denied: only the original author may update review {review_id}{user_suffix} (Domain Rule 2).",
            detail=details,
            status_code=status_code,
        )


class InvalidReviewRatingError(ValidationError):
    """Raised when a review rating falls outside the valid range 1-10 (HTTP 400)."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    default_message: str = "Review rating must be an integer between 1 and 10."

    def __init__(
        self,
        rating: int,
        min_rating: int = 1,
        max_rating: int = 10,
        message: str | None = None,
        detail: dict[str, Any] | None = None,
        status_code: int | None = None,
    ) -> None:
        self.rating = rating
        self.min_rating = min_rating
        self.max_rating = max_rating
        super().__init__(
            message=message
            or f"Invalid review rating {rating}: rating must be between {min_rating} and {max_rating}.",
            detail={
                "rating": rating,
                "min_rating": min_rating,
                "max_rating": max_rating,
                **(detail or {}),
            },
            status_code=status_code,
        )

