from __future__ import annotations

from typing import Sequence
import uuid

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import FilmNotFoundError
from app.dao.film_dao import FilmDAO
from app.models.film import Film, FilmORM


def get_film_dao() -> FilmDAO:
    """Dependency provider returning a FilmDAO instance."""
    return FilmDAO()


class FilmService:
    """
    Thin Service layer for Film business logic and orchestration.
    Receives FilmDAO via constructor injection and receives AsyncSession from routes.
    Contains business logic and raises domain exceptions (FilmNotFoundError) when data is missing.
    Never executes direct SQLAlchemy queries.
    """

    def __init__(self, dao: FilmDAO = Depends(get_film_dao)):
        self.dao = dao

    async def get_by_id(self, session: AsyncSession, film_id: uuid.UUID) -> Film:
        """
        Retrieve a film by UUID or raise domain FilmNotFoundError.
        """
        film = await self.dao.get_by_id(session, film_id)
        if film is None:
            raise FilmNotFoundError(f"Film with id {film_id} not found")
        return film

    async def get_film(self, session: AsyncSession, film_id: uuid.UUID) -> Film:
        """Alias for get_by_id."""
        return await self.get_by_id(session=session, film_id=film_id)

    async def list_films(
        self,
        session: AsyncSession,
        genre: str | None = None,
        year_from: int | None = None,
        year_to: int | None = None,
        start_year: int | None = None,
        end_year: int | None = None,
        limit: int = 10,
    ) -> list[Film]:
        """
        Retrieve films with optional dynamic filtering.
        Normalizes start_year/year_from and end_year/year_to.
        """
        effective_from = year_from if year_from is not None else start_year
        effective_to = year_to if year_to is not None else end_year

        return await self.dao.list_films(
            session=session,
            genre=genre,
            year_from=effective_from,
            year_to=effective_to,
            limit=limit,
        )

    async def create_film(
        self,
        session: AsyncSession,
        title: str,
        director: str,
        release_year: int,
        genre: str,
        description: str = "",
    ) -> Film:
        """
        Validate and create a new film with UUID PK.
        """
        return await self.dao.create(
            session=session,
            title=title.strip(),
            director=director.strip(),
            release_year=release_year,
            genre=genre.strip(),
            description=description.strip(),
        )

    async def update_film(
        self,
        session: AsyncSession,
        film_id: uuid.UUID,
        **updates,
    ) -> Film:
        """
        Update film attributes or raise domain FilmNotFoundError if missing.
        """
        film = await self.dao.update(session, film_id, **updates)
        if film is None:
            raise FilmNotFoundError(f"Film with id {film_id} not found")
        return film

    async def delete_film(
        self,
        session: AsyncSession,
        film_id: uuid.UUID,
    ) -> bool:
        """
        Soft delete a film or raise domain FilmNotFoundError if missing.
        """
        success = await self.dao.soft_delete(session, film_id)
        if not success:
            raise FilmNotFoundError(f"Film with id {film_id} not found")
        return True


# Default instance and module-level helpers for backward compatibility
_default_film_service = FilmService(dao=FilmDAO())


async def list_films(
    db: AsyncSession,
    genre: str | None = None,
    start_year: int | None = None,
    end_year: int | None = None,
    limit: int = 10,
) -> Sequence[FilmORM]:
    return await _default_film_service.list_films(
        session=db,
        genre=genre,
        start_year=start_year,
        end_year=end_year,
        limit=limit,
    )


async def get_film(db: AsyncSession, film_id: uuid.UUID) -> FilmORM:
    return await _default_film_service.get_by_id(session=db, film_id=film_id)


async def create_film(
    db: AsyncSession,
    title: str,
    director: str,
    release_year: int,
    genre: str,
    description: str = "",
) -> FilmORM:
    return await _default_film_service.create_film(
        session=db,
        title=title,
        director=director,
        release_year=release_year,
        genre=genre,
        description=description,
    )


async def update_film(db: AsyncSession, film_id: uuid.UUID, **updates) -> FilmORM:
    return await _default_film_service.update_film(session=db, film_id=film_id, **updates)


async def delete_film(db: AsyncSession, film_id: uuid.UUID) -> bool:
    return await _default_film_service.delete_film(session=db, film_id=film_id)
