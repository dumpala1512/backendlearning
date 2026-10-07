from __future__ import annotations

from typing import Sequence
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.film import Film
from app.models.review import Review, ReviewORM


class ReviewDAO:
    """
    Data Access Object for Review entities.
    Encapsulates all asynchronous SQLAlchemy 2.0 database queries for reviews.
    Uses UUID for review_id, film_id, and user_id.
    """

    async def list_reviews(
        self,
        session: AsyncSession,
        film_id: uuid.UUID,
        min_rating: int | None = None,
        max_rating: int | None = None,
    ) -> list[Review]:
        """
        Return all reviews for a film, newest first (.order_by(Review.created_at.desc())).
        Supports optional min_rating and max_rating filters.
        """
        query = select(Review).where(Review.film_id == film_id)
        if min_rating is not None:
            query = query.where(Review.rating >= min_rating)
        if max_rating is not None:
            query = query.where(Review.rating <= max_rating)
        query = query.order_by(Review.created_at.desc(), Review.id.desc())

        result = await session.execute(query)
        return list(result.scalars().all())

    async def get_by_film_id(
        self,
        session: AsyncSession,
        film_id: uuid.UUID,
        min_rating: int | None = None,
        max_rating: int | None = None,
    ) -> list[Review]:
        """Alias for list_reviews."""
        return await self.list_reviews(
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
        Compute the average rating for a film using func.avg().
        Returns float or None if there are no reviews for this film.
        """
        query = select(func.avg(Review.rating)).where(Review.film_id == film_id)
        result = await session.execute(query)
        avg_val = result.scalar_one_or_none()
        return float(avg_val) if avg_val is not None else None

    async def create(
        self,
        session: AsyncSession,
        film_id: uuid.UUID,
        rating: int,
        review: str,
        reviewer_display_name: str = "Anonymous Critic",
        user_id: uuid.UUID | None = None,
    ) -> Review:
        """
        Persist a new review in PostgreSQL with UUID PK.
        Returns the created Review entity.
        """
        new_review = Review(
            film_id=film_id,
            user_id=user_id,
            rating=rating,
            review=review,
            reviewer_display_name=reviewer_display_name,
        )
        session.add(new_review)
        await session.commit()
        await session.refresh(new_review)
        return new_review

    async def get_by_id(
        self,
        session: AsyncSession,
        review_id: uuid.UUID,
    ) -> Review | None:
        """
        Find a review by UUID ID using select and scalar_one_or_none.
        """
        query = select(Review).where(Review.id == review_id)
        result = await session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_film_and_user(
        self,
        session: AsyncSession,
        film_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Review | None:
        """
        Find a review by film_id and user_id to enforce Rule 1 (one review per user per film).
        """
        query = select(Review).where(Review.film_id == film_id, Review.user_id == user_id)
        result = await session.execute(query)
        return result.scalar_one_or_none()

    async def update(
        self,
        session: AsyncSession,
        review_id: uuid.UUID,
        **fields,
    ) -> Review | None:
        """
        Update review rating or text. Returns updated Review or None if not found.
        """
        item = await self.get_by_id(session, review_id)
        if not item:
            return None
        for key, value in fields.items():
            if value is not None and hasattr(item, key):
                setattr(item, key, value)
        await session.commit()
        await session.refresh(item)
        return item

    async def delete(
        self,
        session: AsyncSession,
        review_id: uuid.UUID,
    ) -> bool:
        """
        Delete a review by UUID identifier.
        Returns True if deleted, False if record does not exist.
        """
        item = await self.get_by_id(session, review_id)
        if not item:
            return False
        await session.delete(item)
        await session.commit()
        return True

    async def get_reviews_with_details(
        self,
        session: AsyncSession,
        film_id: uuid.UUID | None = None,
    ) -> list[Review]:
        """
        Retrieve reviews with joined Film and User details via joinedload.
        """
        query = select(Review).options(
            joinedload(Review.film),
            joinedload(Review.user),
        )
        if film_id is not None:
            query = query.where(Review.film_id == film_id)
        query = query.order_by(Review.created_at.desc())

        result = await session.execute(query)
        return list(result.scalars().all())

    async def count(self, session: AsyncSession, active_only: bool = True) -> int:
        """
        Count total reviews asynchronously via SQLAlchemy func.count.
        Excludes reviews associated with soft-deleted films by default.
        """
        query = select(func.count(Review.id))
        if active_only:
            query = query.join(Film, Review.film_id == Film.id).where(Film.is_active.is_(True))
        result = await session.execute(query)
        return result.scalar_one() or 0


# Default singleton and module-level functions for backward compatibility
default_review_dao = ReviewDAO()


async def list_reviews(
    db: AsyncSession,
    film_id: uuid.UUID,
    min_rating: int | None = None,
    max_rating: int | None = None,
) -> list[Review]:
    return await default_review_dao.list_reviews(
        session=db,
        film_id=film_id,
        min_rating=min_rating,
        max_rating=max_rating,
    )


async def get_by_film_id(
    db: AsyncSession,
    film_id: uuid.UUID,
    min_rating: int | None = None,
    max_rating: int | None = None,
) -> Sequence[Review]:
    return await default_review_dao.get_by_film_id(
        session=db,
        film_id=film_id,
        min_rating=min_rating,
        max_rating=max_rating,
    )


async def average_rating(db: AsyncSession, film_id: uuid.UUID) -> float | None:
    return await default_review_dao.average_rating(session=db, film_id=film_id)


async def get_reviews_with_details(
    db: AsyncSession,
    film_id: uuid.UUID | None = None,
) -> Sequence[Review]:
    return await default_review_dao.get_reviews_with_details(session=db, film_id=film_id)


async def get_by_id(db: AsyncSession, review_id: uuid.UUID) -> Review | None:
    return await default_review_dao.get_by_id(session=db, review_id=review_id)


async def create(
    db: AsyncSession,
    film_id: uuid.UUID,
    rating: int,
    review: str,
    reviewer_display_name: str = "Anonymous Critic",
    user_id: uuid.UUID | None = None,
) -> Review:
    return await default_review_dao.create(
        session=db,
        film_id=film_id,
        rating=rating,
        review=review,
        reviewer_display_name=reviewer_display_name,
        user_id=user_id,
    )


async def update(db: AsyncSession, review_id: uuid.UUID, **fields) -> Review | None:
    return await default_review_dao.update(session=db, review_id=review_id, **fields)


async def delete(db: AsyncSession, review_id: uuid.UUID) -> bool:
    return await default_review_dao.delete(session=db, review_id=review_id)


async def count(db: AsyncSession) -> int:
    return await default_review_dao.count(session=db)


get_by_film_id_async = get_by_film_id
get_reviews_with_details_async = get_reviews_with_details
get_by_id_async = get_by_id
create_async = create
update_async = update
delete_async = delete
count_async = count
