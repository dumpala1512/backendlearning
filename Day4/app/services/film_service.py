from __future__ import annotations

from typing import Sequence
from sqlalchemy.ext.asyncio import AsyncSession

from app.dao import film_dao
from app.schemas import FilmORM


async def list_films(
    db: AsyncSession,
    genre: str | None = None,
    start_year: int | None = None,
    end_year: int | None = None,
    limit: int = 10,
) -> Sequence[FilmORM]:
    """Retrieve films from PostgreSQL with optional filtering."""
    return await film_dao.get_all(
        db=db,
        genre=genre,
        start_year=start_year,
        end_year=end_year,
        limit=limit,
    )


async def get_film(db: AsyncSession, film_id: int) -> FilmORM | None:
    """Retrieve a single film by ID from PostgreSQL."""
    return await film_dao.get_by_id(db=db, film_id=film_id)


async def create_film(
    db: AsyncSession,
    title: str,
    director: str,
    release_year: int,
    genre: str,
    description: str = "",
) -> FilmORM:
    """Validate and create a new film in PostgreSQL."""
    return await film_dao.create(
        db=db,
        title=title.strip(),
        director=director.strip(),
        release_year=release_year,
        genre=genre.strip(),
        description=description.strip(),
    )


async def update_film(db: AsyncSession, film_id: int, **updates) -> FilmORM | None:
    """Update existing film details in PostgreSQL."""
    return await film_dao.update(db=db, film_id=film_id, **updates)


async def delete_film(db: AsyncSession, film_id: int) -> bool:
    """Remove a film from PostgreSQL."""
    return await film_dao.delete(db=db, film_id=film_id)
