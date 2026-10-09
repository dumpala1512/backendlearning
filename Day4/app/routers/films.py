from __future__ import annotations

import logging
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import project_config
from app.dependencies import get_current_user, get_db, get_film_service, get_request_id, require_role
from app.schemas.common import MessageResponse
from app.schemas.film import FilmCreate, FilmFilterQuery, FilmResponse, FilmUpdate
from app.services.film_service import FilmService

logger = logging.getLogger("film_review.routers.films")

router = APIRouter(prefix="/films", tags=["Films"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[FilmResponse], summary="List all films")
async def list_films(
    genre: str | None = Query(None, description="Filter films by genre"),
    start_year: int | None = Query(None, ge=1888, le=2100, description="Filter by minimum release year"),
    end_year: int | None = Query(None, ge=1888, le=2100, description="Filter by maximum release year"),
    limit: int = Query(10, ge=1, le=100, description="Max number of films to return"),
    service: FilmService = Depends(get_film_service),
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id),
) -> list[FilmResponse]:
    """
    Retrieve all films with optional genre and validated year range filters.
    Follows: Route -> Service -> DAO -> AsyncSession -> Database.
    """
    logger.info(
        f"[{request_id}] list_films called | API {project_config.API_VERSION} | "
        f"DB Session active={db.is_active}"
    )

    # Validate range filters via schema
    FilmFilterQuery(
        genre=genre,
        start_year=start_year,
        end_year=end_year,
        limit=limit,
    )

    films = await service.list_films(
        session=db,
        genre=genre,
        year_from=start_year,
        year_to=end_year,
        limit=limit,
    )
    return [FilmResponse.model_validate(f) for f in films]


@router.get("/{film_id}", response_model=FilmResponse, summary="Get film by ID")
async def get_film(
    film_id: uuid.UUID,
    service: FilmService = Depends(get_film_service),
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id),
) -> FilmResponse:
    """
    Retrieve a single film by UUID ID.
    Follows: Route -> Service -> DAO -> AsyncSession -> Database.
    """
    logger.info(
        f"[{request_id}] get_film({film_id}) | API {project_config.API_VERSION} | "
        f"DB Session active={db.is_active}"
    )
    film = await service.get_by_id(session=db, film_id=film_id)
    return FilmResponse.model_validate(film)


@router.post(
    "",
    response_model=FilmResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new film",
    dependencies=[Depends(get_current_user), Depends(require_role("admin"))],
)
async def create_film(
    payload: FilmCreate,
    service: FilmService = Depends(get_film_service),
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id),
) -> FilmResponse:
    """
    Create a new film in PostgreSQL (Admin only).
    Follows: Route -> Service -> DAO -> AsyncSession -> Database.
    """
    logger.info(
        f"[{request_id}] create_film '{payload.title}' | API {project_config.API_VERSION} | "
        f"DB active={db.is_active}"
    )
    film = await service.create_film(
        session=db,
        title=payload.title,
        director=payload.director,
        release_year=payload.release_year,
        genre=payload.genre,
        description=payload.description,
    )
    return FilmResponse.model_validate(film)


@router.patch(
    "/{film_id}",
    response_model=FilmResponse,
    summary="Partially update a film",
    dependencies=[Depends(get_current_user), Depends(require_role("admin"))],
)
async def update_film(
    film_id: uuid.UUID,
    payload: FilmUpdate,
    service: FilmService = Depends(get_film_service),
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id),
) -> FilmResponse:
    """
    Partially update an existing film in PostgreSQL (Admin only).
    Follows: Route -> Service -> DAO -> AsyncSession -> Database.
    """
    logger.info(f"[{request_id}] update_film({film_id}) | DB active={db.is_active}")
    film = await service.update_film(
        session=db,
        film_id=film_id,
        **payload.model_dump(exclude_unset=True),
    )
    return FilmResponse.model_validate(film)


@router.delete(
    "/{film_id}",
    response_model=MessageResponse,
    summary="Delete a film",
    dependencies=[Depends(get_current_user), Depends(require_role("admin"))],
)
async def delete_film(
    film_id: uuid.UUID,
    service: FilmService = Depends(get_film_service),
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id),
) -> MessageResponse:
    """
    Soft delete a film by UUID ID (Admin only).
    Follows: Route -> Service -> DAO -> AsyncSession -> Database.
    """
    logger.info(f"[{request_id}] delete_film({film_id}) | DB active={db.is_active}")
    await service.delete_film(session=db, film_id=film_id)
    return MessageResponse(message=f"Film {film_id} successfully deleted", success=True)
