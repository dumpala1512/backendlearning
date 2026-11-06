from datetime import datetime
from typing import Any, Sequence
import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.film import Film
from app.models.review import Review, ReviewORM
from app.models.user import User


class ReviewDAO:
    """
    Data Access Object for Review entities.
    Encapsulates all asynchronous SQLAlchemy 2.0 database queries for reviews.
    Uses UUID for review_id, film_id, and user_id.
    """

    def _build_review_filter_conditions(
        self,
        film_id: uuid.UUID,
        min_rating: int | None = None,
        max_rating: int | None = None,
        reviewer: str | None = None,
        username: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> list[Any]:
        """
        Dynamically build review filter conditions at runtime.
        Only supplied filter criteria are appended and executed in a single where() call.
        """
        conditions: list[Any] = [Review.film_id == film_id]
        if min_rating is not None:
            conditions.append(Review.rating >= min_rating)
        if max_rating is not None:
            conditions.append(Review.rating <= max_rating)

        author_filter = reviewer or username
        if author_filter is not None and author_filter.strip():
            term = f"%{author_filter.strip()}%"
            conditions.append(
                or_(
                    Review.reviewer_display_name.ilike(term),
                    Review.user.has(User.username.ilike(term)),
                )
            )

        if date_from is not None:
            conditions.append(Review.created_at >= date_from)
        if date_to is not None:
            conditions.append(Review.created_at <= date_to)

        return conditions

    async def list_reviews_paginated(
        self,
        session: AsyncSession,
        film_id: uuid.UUID,
        min_rating: int | None = None,
        max_rating: int | None = None,
        reviewer: str | None = None,
        username: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        page: int = 1,
        limit: int = 10,
        page_size: int | None = None,
    ) -> tuple[list[Review], int]:
        """
        Perform offset-based pagination directly in SQL using OFFSET and LIMIT for reviews.
        Computes total matching record count via efficient COUNT query.
        Applies eager loading using joinedload to eliminate N+1 queries.
        Standardized on `limit` with `page_size` alias.
        """
        effective_limit = page_size if page_size is not None else limit
        conditions = self._build_review_filter_conditions(
            film_id=film_id,
            min_rating=min_rating,
            max_rating=max_rating,
            reviewer=reviewer,
            username=username,
            date_from=date_from,
            date_to=date_to,
        )

        # 1. Efficient count query for matching reviews
        count_query = select(func.count(Review.id)).where(*conditions)
        count_res = await session.execute(count_query)
        total = count_res.scalar_one() or 0

        # 2. Paginated data query using SQL OFFSET and LIMIT with eager loading
        query = (
            select(Review)
            .options(
                joinedload(Review.user),
                joinedload(Review.film),
            )
            .where(*conditions)
        )
        offset_val = max(0, (page - 1) * effective_limit)
        query = (
            query.order_by(Review.created_at.desc(), Review.id.desc())
            .offset(offset_val)
            .limit(effective_limit)
        )

        result = await session.execute(query)
        reviews = list(result.scalars().all())
        return reviews, total

    async def list_reviews(
        self,
        session: AsyncSession,
        film_id: uuid.UUID,
        min_rating: int | None = None,
        max_rating: int | None = None,
        reviewer: str | None = None,
        username: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[Review]:
        """
        Return all reviews for a film, newest first (.order_by(Review.created_at.desc())).
        Supports optional min_rating, max_rating, reviewer, date_from, and date_to filters.
        Eagerly loads user and film relationships to eliminate N+1 queries.
        """
        conditions = self._build_review_filter_conditions(
            film_id=film_id,
            min_rating=min_rating,
            max_rating=max_rating,
            reviewer=reviewer,
            username=username,
            date_from=date_from,
            date_to=date_to,
        )
        query = (
            select(Review)
            .options(
                joinedload(Review.user),
                joinedload(Review.film),
            )
            .where(*conditions)
            .order_by(Review.created_at.desc(), Review.id.desc())
        )
        if offset is not None:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)

        result = await session.execute(query)
        return list(result.scalars().all())

    async def get_by_film_id(
        self,
        session: AsyncSession,
        film_id: uuid.UUID,
        min_rating: int | None = None,
        max_rating: int | None = None,
        reviewer: str | None = None,
        username: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> list[Review]:
        """Alias for list_reviews."""
        return await self.list_reviews(
            session=session,
            film_id=film_id,
            min_rating=min_rating,
            max_rating=max_rating,
            reviewer=reviewer,
            username=username,
            date_from=date_from,
            date_to=date_to,
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

    async def count_by_film_id(
        self,
        session: AsyncSession,
        film_id: uuid.UUID,
    ) -> int:
        """
        Count total reviews for a specific film.
        """
        query = select(func.count(Review.id)).where(Review.film_id == film_id)
        result = await session.execute(query)
        return result.scalar_one() or 0

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

    async def overall_average_rating(self, session: AsyncSession, active_only: bool = True) -> float | None:
        """
        Calculate the overall average rating across all reviews.
        Returns float rounded to 2 decimal places or None if no reviews exist.
        """
        query = select(func.avg(Review.rating))
        if active_only:
            query = query.join(Film, Review.film_id == Film.id).where(Film.is_active.is_(True))
        result = await session.execute(query)
        avg = result.scalar_one_or_none()
        if avg is None and active_only:
            query_fb = select(func.avg(Review.rating))
            result_fb = await session.execute(query_fb)
            avg = result_fb.scalar_one_or_none()
        return round(float(avg), 2) if avg is not None else None

    async def get_top_reviewer(self, session: AsyncSession) -> str | None:
        """
        Find the username of the user who has submitted the most reviews.
        """
        query = (
            select(User.username)
            .join(Review, Review.user_id == User.id)
            .group_by(User.id, User.username)
            .order_by(func.count(Review.id).desc())
            .limit(1)
        )
        result = await session.execute(query)
        top_user = result.scalar_one_or_none()
        if not top_user:
            query_disp = (
                select(Review.reviewer_display_name)
                .where(Review.reviewer_display_name.is_not(None))
                .group_by(Review.reviewer_display_name)
                .order_by(func.count(Review.id).desc())
                .limit(1)
            )
            res_disp = await session.execute(query_disp)
            top_user = res_disp.scalar_one_or_none()
        return top_user


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


async def count_by_film_id(db: AsyncSession, film_id: uuid.UUID) -> int:
    return await default_review_dao.count_by_film_id(session=db, film_id=film_id)


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
