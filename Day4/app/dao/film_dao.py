from __future__ import annotations

from typing import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas import FilmORM


async def get_all(
    db: AsyncSession,
    genre: str | None = None,
    start_year: int | None = None,
    end_year: int | None = None,
    limit: int = 10,
) -> Sequence[FilmORM]:
    """
    Retrieve all films asynchronously from PostgreSQL using SQLAlchemy 2.0 select.
    Supports optional genre and release year boundary filters.
    """
    query = select(FilmORM)
    if genre:
        query = query.where(func.lower(FilmORM.genre) == genre.strip().lower())
    if start_year is not None:
        query = query.where(FilmORM.release_year >= start_year)
    if end_year is not None:
        query = query.where(FilmORM.release_year <= end_year)
    query = query.order_by(FilmORM.id.asc()).limit(limit)

    result = await db.execute(query)
    return result.scalars().all()


async def get_by_id(db: AsyncSession, film_id: int) -> FilmORM | None:
    """Find a single film by its primary key asynchronously."""
    query = select(FilmORM).where(FilmORM.id == film_id)
    result = await db.execute(query)
    return result.scalars().first()


async def create(
    db: AsyncSession,
    title: str,
    director: str,
    release_year: int,
    genre: str,
    description: str = "",
) -> FilmORM:
    """Insert a new film into PostgreSQL asynchronously."""
    new_film = FilmORM(
        title=title,
        director=director,
        release_year=release_year,
        genre=genre,
        description=description,
    )
    db.add(new_film)
    await db.commit()
    await db.refresh(new_film)
    return new_film


async def update(db: AsyncSession, film_id: int, **fields) -> FilmORM | None:
    """Update film attributes asynchronously."""
    film = await get_by_id(db, film_id)
    if not film:
        return None
    for key, value in fields.items():
        if value is not None and hasattr(film, key):
            setattr(film, key, value)
    await db.commit()
    await db.refresh(film)
    return film


async def delete(db: AsyncSession, film_id: int) -> bool:
    """Delete a film by ID asynchronously."""
    film = await get_by_id(db, film_id)
    if not film:
        return False
    await db.delete(film)
    await db.commit()
    return True


async def count(db: AsyncSession) -> int:
    """Return total number of films asynchronously via SQLAlchemy."""
    query = select(func.count(FilmORM.id))
    result = await db.execute(query)
    return result.scalar_one() or 0


# Backwards compatibility alias
count_async = count
