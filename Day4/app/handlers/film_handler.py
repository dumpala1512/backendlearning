from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.common import MessageResponse
from app.models.film import FilmCreate, FilmFilterQuery, FilmResponse, FilmUpdate
from app.services import film_service


async def get_all_films(
    db: AsyncSession,
    query: FilmFilterQuery | None = None,
) -> list[FilmResponse]:
    """Fetch films via film_service with optional filtering and convert to FilmResponse models."""
    genre = query.genre if query else None
    start_year = query.start_year if query else None
    end_year = query.end_year if query else None
    limit = query.limit if query else 10

    films = await film_service.list_films(
        db=db,
        genre=genre,
        start_year=start_year,
        end_year=end_year,
        limit=limit,
    )
    return [FilmResponse.model_validate(f) for f in films]


async def get_film_by_id(db: AsyncSession, film_id: int) -> FilmResponse:
    """Fetch a single film via film_service or raise 404."""
    film = await film_service.get_film(db=db, film_id=film_id)
    if not film:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Film with id {film_id} not found",
        )
    return FilmResponse.model_validate(film)


async def create_film(db: AsyncSession, payload: FilmCreate) -> FilmResponse:
    """Create a new film via film_service and return validated FilmResponse."""
    film = await film_service.create_film(
        db=db,
        title=payload.title,
        director=payload.director,
        release_year=payload.release_year,
        genre=payload.genre,
        description=payload.description,
    )
    return FilmResponse.model_validate(film)


async def update_film(
    db: AsyncSession,
    film_id: int,
    payload: FilmUpdate,
) -> FilmResponse:
    """Update a film via film_service using model_dump(exclude_unset=True) or raise 404."""
    film = await film_service.update_film(
        db=db,
        film_id=film_id,
        **payload.model_dump(exclude_unset=True),
    )
    if not film:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Film with id {film_id} not found",
        )
    return FilmResponse.model_validate(film)


async def delete_film(db: AsyncSession, film_id: int) -> MessageResponse:
    """Delete a film via film_service or raise 404."""
    deleted = await film_service.delete_film(db=db, film_id=film_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Film with id {film_id} not found",
        )
    return MessageResponse(message=f"Film {film_id} successfully deleted", success=True)
