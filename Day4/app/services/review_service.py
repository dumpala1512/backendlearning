from __future__ import annotations

from typing import Sequence
from sqlalchemy.ext.asyncio import AsyncSession

from app.dao import film_dao, review_dao
from app.schemas import ReviewORM


async def get_film_reviews(
    db: AsyncSession,
    film_id: int,
    min_rating: int | None = None,
    max_rating: int | None = None,
) -> Sequence[ReviewORM] | None:
    """Get all reviews for a film or return None if film does not exist."""
    film = await film_dao.get_by_id(db=db, film_id=film_id)
    if not film:
        return None
    return await review_dao.get_by_film_id(
        db=db,
        film_id=film_id,
        min_rating=min_rating,
        max_rating=max_rating,
    )


async def add_review(
    db: AsyncSession,
    film_id: int,
    rating: int,
    review: str,
    reviewer_display_name: str = "Anonymous Critic",
    user_id: int | None = None,
) -> ReviewORM | None:
    """Validate film existence and persist new review."""
    film = await film_dao.get_by_id(db=db, film_id=film_id)
    if not film:
        return None
    return await review_dao.create(
        db=db,
        film_id=film_id,
        rating=rating,
        review=review.strip(),
        reviewer_display_name=reviewer_display_name.strip(),
        user_id=user_id,
    )


async def update_review(db: AsyncSession, review_id: int, **updates) -> ReviewORM | None:
    """Update review rating or text."""
    return await review_dao.update(db=db, review_id=review_id, **updates)


async def delete_review(db: AsyncSession, review_id: int) -> bool:
    """Delete review by ID."""
    return await review_dao.delete(db=db, review_id=review_id)
