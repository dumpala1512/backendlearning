from __future__ import annotations

import base64
from datetime import datetime
import json
from typing import Any, Sequence
import uuid

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.film import Film, FilmORM
from app.models.review import Review


class FilmDAO:
    """
    Data Access Object for Film entities.
    Encapsulates all asynchronous SQLAlchemy 2.0 database queries for films.
    The DAO never creates its own AsyncSession and returns None when records are not found.
    """

    async def get_by_id(
        self,
        session: AsyncSession,
        film_id: uuid.UUID,
        active_only: bool = True,
        eager_load_reviews: bool = False,
    ) -> Film | None:
        """
        Retrieve a single film by its UUID primary key.
        Returns active Film or None if missing or soft-deleted.
        Supports eager loading reviews using selectinload to prevent N+1 queries.
        """
        query = select(Film).where(Film.id == film_id)
        if eager_load_reviews:
            query = query.options(selectinload(Film.reviews))
        if active_only:
            query = query.where(Film.is_active.is_(True))
        result = await session.execute(query)
        return result.scalar_one_or_none()

    def _build_film_filter_conditions(
        self,
        genre: str | None = None,
        year_from: int | None = None,
        year_to: int | None = None,
        director: str | None = None,
        active_only: bool = True,
    ) -> list[Any]:
        """
        Build dynamic SQLAlchemy filter conditions at runtime.
        Only supplied filter criteria are appended.
        Applied in a single where(*conditions) call.
        """
        conditions: list[Any] = []
        if active_only:
            conditions.append(Film.is_active.is_(True))
        if genre is not None and genre.strip():
            conditions.append(func.lower(Film.genre) == genre.strip().lower())
        if year_from is not None:
            conditions.append(Film.release_year >= year_from)
        if year_to is not None:
            conditions.append(Film.release_year <= year_to)
        if director is not None and director.strip():
            conditions.append(Film.director.ilike(f"%{director.strip()}%"))
        return conditions

    async def list_films_paginated(
        self,
        session: AsyncSession,
        genre: str | None = None,
        year_from: int | None = None,
        year_to: int | None = None,
        director: str | None = None,
        page: int = 1,
        limit: int = 10,
        page_size: int | None = None,
        active_only: bool = True,
        eager_load_reviews: bool = False,
    ) -> tuple[list[Film], int]:
        """
        Perform offset-based pagination directly in SQL using OFFSET and LIMIT.
        Computes total matching record count via efficient COUNT query.
        Applies eager loading using selectinload to eliminate N+1 queries.
        Standardized on `limit` with `page_size` alias.
        """
        effective_limit = page_size if page_size is not None else limit
        conditions = self._build_film_filter_conditions(
            genre=genre,
            year_from=year_from,
            year_to=year_to,
            director=director,
            active_only=active_only,
        )

        # 1. Efficient COUNT query with same filter conditions
        count_query = select(func.count(Film.id))
        if conditions:
            count_query = count_query.where(*conditions)
        count_res = await session.execute(count_query)
        total = count_res.scalar_one() or 0

        # 2. Paginated data query using SQL OFFSET and LIMIT
        query = select(Film)
        if eager_load_reviews:
            query = query.options(selectinload(Film.reviews))
        if conditions:
            query = query.where(*conditions)

        offset_val = max(0, (page - 1) * effective_limit)
        query = (
            query.order_by(Film.created_at.desc(), Film.id.asc())
            .offset(offset_val)
            .limit(effective_limit)
        )

        result = await session.execute(query)
        films = list(result.scalars().all())
        return films, total

    @staticmethod
    def _decode_cursor(cursor: str | None) -> tuple[datetime | None, uuid.UUID | None]:
        """Decode base64 JSON cursor into (created_at, film_id) tuple."""
        if not cursor or not cursor.strip():
            return None, None
        try:
            data = json.loads(base64.urlsafe_b64decode(cursor.strip().encode()).decode())
            created_str = data.get("last_created_at") or data.get("created_at")
            created_at = datetime.fromisoformat(created_str) if created_str else None
            last_id = uuid.UUID(str(data["last_id"])) if "last_id" in data else None
            return created_at, last_id
        except Exception:
            return None, None

    @staticmethod
    def _encode_cursor(film: Film) -> str:
        """Encode film position marker as opaque base64 JSON cursor string."""
        payload = {
            "last_id": str(film.id),
            "last_created_at": film.created_at.isoformat() if film.created_at else None,
        }
        return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()

    async def list_films_cursor(
        self,
        session: AsyncSession,
        cursor: str | None = None,
        limit: int = 10,
        genre: str | None = None,
        year_from: int | None = None,
        year_to: int | None = None,
        director: str | None = None,
        active_only: bool = True,
        eager_load_reviews: bool = False,
    ) -> tuple[list[Film], str | None]:
        """
        Perform cursor-based pagination as an alternative to offset pagination.
        Returns up to `limit` records and an opaque `next_cursor` (or None when exhausted).
        """
        conditions = self._build_film_filter_conditions(
            genre=genre,
            year_from=year_from,
            year_to=year_to,
            director=director,
            active_only=active_only,
        )

        # 1. Apply cursor filter condition if cursor provided
        last_created, last_id = self._decode_cursor(cursor)
        if last_created and last_id:
            conditions.append(
                or_(
                    Film.created_at < last_created,
                    and_(Film.created_at == last_created, Film.id < last_id),
                )
            )
        elif last_id:
            conditions.append(Film.id != last_id)

        # 2. Query limit + 1 items to determine if a next page exists
        query = select(Film)
        if eager_load_reviews:
            query = query.options(selectinload(Film.reviews))
        if conditions:
            query = query.where(*conditions)

        query = query.order_by(Film.created_at.desc(), Film.id.desc()).limit(limit + 1)
        result = await session.execute(query)
        fetched = list(result.scalars().all())

        # 3. Slice page items and generate opaque next_cursor
        has_more = len(fetched) > limit
        items = fetched[:limit] if has_more else fetched
        next_cursor = self._encode_cursor(items[-1]) if has_more and items else None

        return items, next_cursor

    async def list_films(
        self,
        session: AsyncSession,
        genre: str | None = None,
        year_from: int | None = None,
        year_to: int | None = None,
        director: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        active_only: bool = True,
        eager_load_reviews: bool = False,
    ) -> list[Film]:
        """
        Return multiple films with optional dynamic filters:
        - genre
        - year_from (inclusive minimum release year)
        - year_to (inclusive maximum release year)
        - director (case-insensitive substring)
        - active_only: filters out soft-deleted films (is_active == True)
        Filters are applied only when values are provided in a single where() call.
        """
        conditions = self._build_film_filter_conditions(
            genre=genre,
            year_from=year_from,
            year_to=year_to,
            director=director,
            active_only=active_only,
        )

        query = select(Film)
        if eager_load_reviews:
            query = query.options(selectinload(Film.reviews))
        if conditions:
            query = query.where(*conditions)

        query = query.order_by(Film.created_at.desc(), Film.id.asc())
        if offset is not None:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)

        result = await session.execute(query)
        return list(result.scalars().all())

    async def get_all(
        self,
        session: AsyncSession,
        genre: str | None = None,
        start_year: int | None = None,
        end_year: int | None = None,
        director: str | None = None,
        limit: int = 10,
        active_only: bool = True,
        **kwargs,
    ) -> list[Film]:
        """Backward-compatible helper mapping start_year/end_year to list_films."""
        year_from = start_year if start_year is not None else kwargs.get("year_from")
        year_to = end_year if end_year is not None else kwargs.get("year_to")
        dir_val = director if director is not None else kwargs.get("director")
        return await self.list_films(
            session=session,
            genre=genre,
            year_from=year_from,
            year_to=year_to,
            director=dir_val,
            limit=limit,
            active_only=active_only,
        )

    async def create(
        self,
        session: AsyncSession,
        title: str,
        director: str,
        release_year: int,
        genre: str,
        description: str = "",
        **kwargs,
    ) -> Film:
        """
        Create and persist a new Film entity in PostgreSQL with UUID PK.
        """
        film = Film(
            title=title,
            director=director,
            release_year=release_year,
            genre=genre,
            description=description,
            **kwargs,
        )
        session.add(film)
        await session.commit()
        await session.refresh(film)
        return film

    async def update(
        self,
        session: AsyncSession,
        film_id: uuid.UUID,
        **fields,
    ) -> Film | None:
        """
        Update only the supplied attributes of an existing active film.
        Returns updated Film or None if missing or soft-deleted.
        """
        film = await self.get_by_id(session, film_id, active_only=True)
        if film is None:
            return None

        for key, value in fields.items():
            if hasattr(film, key):
                if value is not None or key == "average_rating":
                    setattr(film, key, value)

        await session.commit()
        await session.refresh(film)
        return film

    async def soft_delete(
        self,
        session: AsyncSession,
        film_id: uuid.UUID,
    ) -> bool:
        """
        Soft delete a film by setting is_active = False without removing the row.
        Returns True if updated, or False if film does not exist or is already soft-deleted.
        """
        film = await self.get_by_id(session, film_id, active_only=True)
        if film is None:
            return False

        film.is_active = False
        await session.commit()
        return True

    async def delete(
        self,
        session: AsyncSession,
        film_id: uuid.UUID,
    ) -> bool:
        """Soft delete a film (delegates to soft_delete)."""
        return await self.soft_delete(session, film_id)

    async def count(self, session: AsyncSession, active_only: bool = True) -> int:
        """
        Return total number of films asynchronously via SQLAlchemy 2.0 select.
        Excludes soft-deleted films by default.
        """
        query = select(func.count(Film.id))
        if active_only:
            query = query.where(Film.is_active.is_(True))
        result = await session.execute(query)
        return result.scalar_one() or 0

    async def search_films(
        self,
        session: AsyncSession,
        search_term: str | None = None,
        active_only: bool = True,
        limit: int | None = 10,
    ) -> list[Film]:
        """
        Search active films by title (case-insensitive substring match).
        If search_term is empty or None, returns all active films up to limit.
        Computes and attaches average_rating to each matching Film instance.
        """
        trimmed = search_term.strip() if search_term else ""

        # Outer join reviews to aggregate average rating per film
        query = (
            select(
                Film,
                func.avg(Review.rating).label("avg_rating"),
            )
            .outerjoin(Review, Review.film_id == Film.id)
        )
        if active_only:
            query = query.where(Film.is_active.is_(True))
        if trimmed:
            query = query.where(Film.title.ilike(f"%{trimmed}%"))

        query = query.group_by(Film.id).order_by(Film.title.asc())
        if limit is not None:
            query = query.limit(limit)

        result = await session.execute(query)
        films: list[Film] = []
        for film, avg_rating in result.all():
            film.average_rating = round(float(avg_rating), 1) if avg_rating is not None else None
            films.append(film)
        return films


# Default singleton and module-level functions for backward compatibility
default_film_dao = FilmDAO()


async def get_by_id(db: AsyncSession, film_id: uuid.UUID) -> Film | None:
    return await default_film_dao.get_by_id(db, film_id)


async def list_films(
    db: AsyncSession,
    genre: str | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    limit: int | None = None,
) -> list[Film]:
    return await default_film_dao.list_films(
        session=db,
        genre=genre,
        year_from=year_from,
        year_to=year_to,
        limit=limit,
    )


async def get_all(
    db: AsyncSession,
    genre: str | None = None,
    start_year: int | None = None,
    end_year: int | None = None,
    limit: int = 10,
) -> Sequence[Film]:
    return await default_film_dao.get_all(
        session=db,
        genre=genre,
        start_year=start_year,
        end_year=end_year,
        limit=limit,
    )


async def create(
    db: AsyncSession,
    title: str,
    director: str,
    release_year: int,
    genre: str,
    description: str = "",
) -> Film:
    return await default_film_dao.create(
        session=db,
        title=title,
        director=director,
        release_year=release_year,
        genre=genre,
        description=description,
    )


async def update(db: AsyncSession, film_id: uuid.UUID, **fields) -> Film | None:
    return await default_film_dao.update(session=db, film_id=film_id, **fields)


async def delete(db: AsyncSession, film_id: uuid.UUID) -> bool:
    return await default_film_dao.delete(session=db, film_id=film_id)


async def count(db: AsyncSession) -> int:
    return await default_film_dao.count(session=db)


count_async = count


async def search_films(
    db: AsyncSession,
    search_term: str | None = None,
    limit: int | None = 10,
) -> list[Film]:
    return await default_film_dao.search_films(session=db, search_term=search_term, limit=limit)
