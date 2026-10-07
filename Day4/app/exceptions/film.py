from __future__ import annotations

from typing import Any
import uuid
from fastapi import status

from app.exceptions.base import DomainError, DuplicateEntityError, EntityNotFoundError


class FilmNotFoundError(EntityNotFoundError):
    """Raised when a specific Film cannot be found (HTTP 404)."""

    status_code: int = status.HTTP_404_NOT_FOUND
    default_message: str = "Film not found."

    def __init__(
        self,
        film_id: uuid.UUID | str,
        message: str | None = None,
        detail: dict[str, Any] | None = None,
        status_code: int | None = None,
    ) -> None:
        self.film_id = film_id
        super().__init__(
            message=message or f"Film with id {film_id} not found.",
            detail={"film_id": str(film_id), **(detail or {})},
            status_code=status_code,
        )


class FilmHasActiveReviewsError(DomainError):
    """
    Raised when attempting to soft delete a film that still has active reviews (HTTP 409).
    Domain Rule 3: A film may not be soft deleted while it still has active reviews.
    """

    status_code: int = status.HTTP_409_CONFLICT
    default_message: str = "Film cannot be deleted while it still has active reviews."

    def __init__(
        self,
        film_id: uuid.UUID | str,
        active_reviews_count: int,
        message: str | None = None,
        detail: dict[str, Any] | None = None,
        status_code: int | None = None,
    ) -> None:
        self.film_id = film_id
        self.active_reviews_count = active_reviews_count
        plural = "s" if active_reviews_count != 1 else ""
        super().__init__(
            message=message
            or f"Film with id {film_id} cannot be deleted while it still has {active_reviews_count} active review{plural} (Domain Rule 3).",
            detail={"film_id": str(film_id), "active_reviews_count": active_reviews_count, **(detail or {})},
            status_code=status_code,
        )


class FilmAlreadyExistsError(DuplicateEntityError):
    """Raised when attempting to create a film that already exists (HTTP 409)."""

    status_code: int = status.HTTP_409_CONFLICT
    default_message: str = "A film with the given title and release year already exists."

    def __init__(
        self,
        title: str,
        release_year: int | None = None,
        message: str | None = None,
        detail: dict[str, Any] | None = None,
        status_code: int | None = None,
    ) -> None:
        self.title = title
        self.release_year = release_year
        year_str = f" ({release_year})" if release_year else ""
        details: dict[str, Any] = {"title": title}
        if release_year is not None:
            details["release_year"] = release_year
        details.update(detail or {})
        super().__init__(
            message=message or f"Film '{title}'{year_str} already exists.",
            detail=details,
            status_code=status_code,
        )

