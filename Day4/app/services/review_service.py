from __future__ import annotations

from typing import Sequence
import uuid

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import FilmNotFoundError, ReviewNotFoundError
from app.dao.film_dao import FilmDAO
from app.dao.review_dao import ReviewDAO
from app.models.review import Review, ReviewORM


def get_film_dao() -> FilmDAO:
    return FilmDAO()


def get_review_dao() -> ReviewDAO:
    return ReviewDAO()


class ReviewService:
    """
    Thin Service layer for Review business logic and orchestration.
    Receives ReviewDAO and FilmDAO via constructor injection and receives AsyncSession from routes.
    Decides when to raise domain exceptions (FilmNotFoundError, ReviewNotFoundError).
    Uses UUID for entities.
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
        Retrieve reviews for a film, ensuring the film exists first.
        """
        film = await self.film_dao.get_by_id(session, film_id)
        if film is None:
            raise FilmNotFoundError(f"Film with id {film_id} not found")

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
        Compute average rating for a film, ensuring film exists.
        """
        film = await self.film_dao.get_by_id(session, film_id)
        if film is None:
            raise FilmNotFoundError(f"Film with id {film_id} not found")

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
        Validate film existence and create a new review.
        """
        film = await self.film_dao.get_by_id(session, film_id)
        if film is None:
            raise FilmNotFoundError(f"Film with id {film_id} not found")

        return await self.dao.create(
            session=session,
            film_id=film_id,
            rating=rating,
            review=review.strip(),
            reviewer_display_name=reviewer_display_name.strip(),
            user_id=user_id,
        )

    async def get_by_id(
        self,
        session: AsyncSession,
        review_id: uuid.UUID,
    ) -> Review:
        """Retrieve a review by UUID or raise ReviewNotFoundError."""
        review = await self.dao.get_by_id(session, review_id)
        if review is None:
            raise ReviewNotFoundError(f"Review with id {review_id} not found")
        return review

    async def update_review(
        self,
        session: AsyncSession,
        review_id: uuid.UUID,
        **updates,
    ) -> Review:
        """Update review content or rating, raising ReviewNotFoundError if missing."""
        review = await self.dao.update(session=session, review_id=review_id, **updates)
        if review is None:
            raise ReviewNotFoundError(f"Review with id {review_id} not found")
        return review

    async def delete_review(
        self,
        session: AsyncSession,
        review_id: uuid.UUID,
    ) -> bool:
        """Delete a review or raise ReviewNotFoundError if missing."""
        deleted = await self.dao.delete(session=session, review_id=review_id)
        if not deleted:
            raise ReviewNotFoundError(f"Review with id {review_id} not found")
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
    except FilmNotFoundError:
        return None


async def update_review(db: AsyncSession, review_id: uuid.UUID, **updates) -> ReviewORM | None:
    try:
        return await _default_review_service.update_review(
            session=db,
            review_id=review_id,
            **updates,
        )
    except ReviewNotFoundError:
        return None


async def delete_review(db: AsyncSession, review_id: uuid.UUID) -> bool:
    try:
        return await _default_review_service.delete_review(session=db, review_id=review_id)
    except ReviewNotFoundError:
        return False
