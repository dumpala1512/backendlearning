from __future__ import annotations

import logging
from typing import Sequence
import uuid

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dao.film_dao import FilmDAO
from app.dao.review_dao import ReviewDAO
from app.exceptions.film import FilmNotFoundError
from app.exceptions.review import (
    ReviewAlreadyExistsError,
    ReviewNotFoundError,
    ReviewPermissionDeniedError,
)
from app.models.review import Review, ReviewORM

logger = logging.getLogger("review_service")


def get_film_dao() -> FilmDAO:
    return FilmDAO()


def get_review_dao() -> ReviewDAO:
    return ReviewDAO()


class ReviewService:
    """
    Service layer for Review business logic, domain rules, and orchestration.
    Receives ReviewDAO and FilmDAO via dependency injection and AsyncSession from caller.
    Enforces business rules (Rule 1: one review per film per user; Rule 2: author-only updates).
    Never executes direct SQLAlchemy queries.
    """

    def __init__(
        self,
        dao: ReviewDAO = Depends(get_review_dao),
        film_dao: FilmDAO = Depends(get_film_dao),
    ):
        self.dao = dao
        self.film_dao = film_dao

    async def list_reviews(
        self,
        session: AsyncSession,
        film_id: uuid.UUID,
        min_rating: int | None = None,
        max_rating: int | None = None,
    ) -> list[Review]:
        """
        Retrieve reviews for a film, ensuring the film exists and is active.
        """
        film = await self.film_dao.get_by_id(session, film_id)
        if film is None:
            raise FilmNotFoundError(film_id=film_id)

        return await self.dao.list_reviews(
            session=session,
            film_id=film_id,
            min_rating=min_rating,
            max_rating=max_rating,
        )

    async def average_rating(
        self,
        session: AsyncSession,
        film_id: uuid.UUID,
    ) -> float | None:
        """
        Compute average rating for a film, ensuring film exists and is active.
        """
        film = await self.film_dao.get_by_id(session, film_id)
        if film is None:
            raise FilmNotFoundError(film_id=film_id)

        return await self.dao.average_rating(session=session, film_id=film_id)

    async def add_review(
        self,
        session: AsyncSession,
        film_id: uuid.UUID,
        rating: int,
        review: str,
        reviewer_display_name: str = "Anonymous Critic",
        user_id: uuid.UUID | None = None,
    ) -> Review:
        """
        Validate film existence and create a new review adhering to Rule 1.
        Rule 1: A user may submit only one review per film.
        """
        film = await self.film_dao.get_by_id(session, film_id)
        if film is None:
            raise FilmNotFoundError(film_id=film_id)

        # Enforce Rule 1: A user may submit only one review per film
        if user_id is not None:
            existing_review = await self.dao.get_by_film_and_user(
                session=session,
                film_id=film_id,
                user_id=user_id,
            )
            if existing_review is not None:
                logger.warning(
                    "Duplicate review attempt: user %s has already reviewed film %s",
                    user_id,
                    film_id,
                    extra={"film_id": str(film_id), "user_id": str(user_id)},
                )
                raise ReviewAlreadyExistsError(
                    film_id=film_id,
                    user_id=user_id,
                    review_id=existing_review.id,
                )

        new_review = await self.dao.create(
            session=session,
            film_id=film_id,
            rating=rating,
            review=review.strip(),
            reviewer_display_name=reviewer_display_name.strip(),
            user_id=user_id,
        )
        logger.info(
            "Review submitted successfully with id %s for film %s",
            new_review.id,
            film_id,
            extra={"review_id": str(new_review.id), "film_id": str(film_id)},
        )
        return new_review

    async def get_by_id(
        self,
        session: AsyncSession,
        review_id: uuid.UUID,
    ) -> Review:
        """Retrieve a review by UUID or raise domain ReviewNotFoundError."""
        review = await self.dao.get_by_id(session, review_id)
        if review is None:
            raise ReviewNotFoundError(review_id=review_id)
        return review

    async def update_review(
        self,
        session: AsyncSession,
        review_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
        **updates,
    ) -> Review:
        """
        Update review content or rating adhering to Rule 2.
        Rule 2: Only the original author may update review rating and review body.
        """
        review = await self.dao.get_by_id(session, review_id)
        if review is None:
            raise ReviewNotFoundError(review_id=review_id)

        # Enforce Rule 2: Only the original author may update
        if review.user_id is not None:
            if user_id is None or review.user_id != user_id:
                logger.warning(
                    "Unauthorized review update attempt on %s by user %s (author is %s)",
                    review_id,
                    user_id,
                    review.user_id,
                    extra={
                        "review_id": str(review_id),
                        "user_id": str(user_id) if user_id else None,
                        "author_id": str(review.user_id),
                    },
                )
                raise ReviewPermissionDeniedError(
                    review_id=review_id,
                    user_id=user_id,
                )

        updated = await self.dao.update(session=session, review_id=review_id, **updates)
        if updated is None:
            raise ReviewNotFoundError(review_id=review_id)

        logger.info(
            "Review %s updated successfully",
            review_id,
            extra={"review_id": str(review_id)},
        )
        return updated

    async def delete_review(
        self,
        session: AsyncSession,
        review_id: uuid.UUID,
    ) -> bool:
        """Delete a review or raise ReviewNotFoundError if missing."""
        review = await self.dao.get_by_id(session, review_id)
        if review is None:
            raise ReviewNotFoundError(review_id=review_id)

        deleted = await self.dao.delete(session=session, review_id=review_id)
        if not deleted:
            raise ReviewNotFoundError(review_id=review_id)

        logger.info(
            "Review %s deleted successfully",
            review_id,
            extra={"review_id": str(review_id)},
        )
        return True

    async def get_reviews_with_details(
        self,
        session: AsyncSession,
        film_id: uuid.UUID | None = None,
    ) -> list[Review]:
        return await self.dao.get_reviews_with_details(session=session, film_id=film_id)


# Default singleton and module-level helpers for backward compatibility
_default_review_service = ReviewService(dao=ReviewDAO(), film_dao=FilmDAO())


async def get_film_reviews(
    db: AsyncSession,
    film_id: uuid.UUID,
    min_rating: int | None = None,
    max_rating: int | None = None,
) -> Sequence[ReviewORM] | None:
    try:
        return await _default_review_service.list_reviews(
            session=db,
            film_id=film_id,
            min_rating=min_rating,
            max_rating=max_rating,
        )
    except FilmNotFoundError:
        return None


async def add_review(
    db: AsyncSession,
    film_id: uuid.UUID,
    rating: int,
    review: str,
    reviewer_display_name: str = "Anonymous Critic",
    user_id: uuid.UUID | None = None,
) -> ReviewORM | None:
    try:
        return await _default_review_service.add_review(
            session=db,
            film_id=film_id,
            rating=rating,
            review=review,
            reviewer_display_name=reviewer_display_name,
            user_id=user_id,
        )
    except (FilmNotFoundError, ReviewAlreadyExistsError):
        return None


async def update_review(db: AsyncSession, review_id: uuid.UUID, **updates) -> ReviewORM | None:
    try:
        return await _default_review_service.update_review(
            session=db,
            review_id=review_id,
            **updates,
        )
    except (ReviewNotFoundError, ReviewPermissionDeniedError):
        return None


async def delete_review(db: AsyncSession, review_id: uuid.UUID) -> bool:
    try:
        return await _default_review_service.delete_review(session=db, review_id=review_id)
    except ReviewNotFoundError:
        return False
