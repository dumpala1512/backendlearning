from __future__ import annotations

from typing import Sequence
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.film import Film, FilmORM


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
    ) -> Film | None:
        """
        Retrieve a single film by its UUID primary key.
        Returns active Film or None if missing or soft-deleted.
        """
        query = select(Film).where(Film.id == film_id)
        if active_only:
            query = query.where(Film.is_active.is_(True))
        result = await session.execute(query)
        return result.scalar_one_or_none()

    async def list_films(
        self,
        session: AsyncSession,
        genre: str | None = None,
        year_from: int | None = None,
        year_to: int | None = None,
        limit: int | None = None,
        active_only: bool = True,
    ) -> list[Film]:
        """
        Return multiple films with optional dynamic filters:
        - genre
        - year_from (inclusive minimum release year)
        - year_to (inclusive maximum release year)
        - active_only: filters out soft-deleted films (is_active == True)
        Filters are applied only when values are provided.
        """
        query = select(Film)
        if active_only:
            query = query.where(Film.is_active.is_(True))
        if genre is not None and genre.strip():
            query = query.where(func.lower(Film.genre) == genre.strip().lower())
        if year_from is not None:
            query = query.where(Film.release_year >= year_from)
        if year_to is not None:
            query = query.where(Film.release_year <= year_to)

        query = query.order_by(Film.created_at.desc(), Film.id.asc())
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
        limit: int = 10,
        active_only: bool = True,
        **kwargs,
    ) -> list[Film]:
        """Backward-compatible helper mapping start_year/end_year to list_films."""
        year_from = start_year if start_year is not None else kwargs.get("year_from")
        year_to = end_year if end_year is not None else kwargs.get("year_to")
        return await self.list_films(
            session=session,
            genre=genre,
            year_from=year_from,
            year_to=year_to,
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
            if value is not None and hasattr(film, key):
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
