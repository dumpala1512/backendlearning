from __future__ import annotations

from typing import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.schemas import ReviewORM


async def get_by_film_id(
    db: AsyncSession,
    film_id: int,
    min_rating: int | None = None,
    max_rating: int | None = None,
) -> Sequence[ReviewORM]:
    """Retrieve reviews for a film with optional rating filters asynchronously via SQLAlchemy."""
    query = select(ReviewORM).where(ReviewORM.film_id == film_id)
    if min_rating is not None:
        query = query.where(ReviewORM.rating >= min_rating)
    if max_rating is not None:
        query = query.where(ReviewORM.rating <= max_rating)
    query = query.order_by(ReviewORM.id.asc())

    result = await db.execute(query)
    return result.scalars().all()


async def get_reviews_with_details(
    db: AsyncSession,
    film_id: int | None = None,
) -> Sequence[ReviewORM]:
    """
    Retrieve reviews loaded together with film title and reviewer username
    in a single database query using joinedload.
    """
    query = select(ReviewORM).options(
        joinedload(ReviewORM.film),
        joinedload(ReviewORM.user),
    )
    if film_id is not None:
        query = query.where(ReviewORM.film_id == film_id)
    query = query.order_by(ReviewORM.id.asc())

    result = await db.execute(query)
    return result.scalars().all()


async def get_by_id(db: AsyncSession, review_id: int) -> ReviewORM | None:
    """Find a review by ID asynchronously via SQLAlchemy."""
    query = select(ReviewORM).where(ReviewORM.id == review_id)
    result = await db.execute(query)
    return result.scalars().first()


async def create(
    db: AsyncSession,
    film_id: int,
    rating: int,
    review: str,
    reviewer_display_name: str = "Anonymous Critic",
    user_id: int | None = None,
) -> ReviewORM:
    """Insert a new review asynchronously into PostgreSQL."""
    new_review = ReviewORM(
        film_id=film_id,
        user_id=user_id,
        rating=rating,
        review=review,
        reviewer_display_name=reviewer_display_name,
    )
    db.add(new_review)
    await db.commit()
    await db.refresh(new_review)
    return new_review


async def update(db: AsyncSession, review_id: int, **fields) -> ReviewORM | None:
    """Update review rating or text asynchronously via SQLAlchemy."""
    item = await get_by_id(db, review_id)
    if not item:
        return None
    for key, value in fields.items():
        if value is not None and hasattr(item, key):
            setattr(item, key, value)
    await db.commit()
    await db.refresh(item)
    return item


async def delete(db: AsyncSession, review_id: int) -> bool:
    """Delete a review asynchronously via SQLAlchemy."""
    item = await get_by_id(db, review_id)
    if not item:
        return False
    await db.delete(item)
    await db.commit()
    return True


async def count(db: AsyncSession) -> int:
    """Count reviews asynchronously via SQLAlchemy."""
    query = select(func.count(ReviewORM.id))
    result = await db.execute(query)
    return result.scalar_one() or 0


# Backwards compatibility aliases
get_by_film_id_async = get_by_film_id
get_reviews_with_details_async = get_reviews_with_details
get_by_id_async = get_by_id
create_async = create
update_async = update
delete_async = delete
count_async = count
