from __future__ import annotations

import logging
from fastapi import APIRouter, Depends, Query, Response, status

from app.core import proj
from app.dependencies import DatabaseSession, get_db, get_trace_id
from app.handlers import film_handler
from app.models.common import MessageResponse
from app.models.film import FilmCreate, FilmFilterQuery, FilmResponse, FilmUpdate

logger = logging.getLogger("film_review.routers.films")

router = APIRouter(prefix="/films", tags=["Films"])


@router.get("", response_model=list[FilmResponse], summary="List all films")
async def list_films(
    response: Response,
    genre: str | None = Query(None, description="Filter films by genre"),
    start_year: int | None = Query(None, ge=1888, le=2100, description="Filter by minimum release year"),
    end_year: int | None = Query(None, ge=1888, le=2100, description="Filter by maximum release year"),
    limit: int = Query(10, ge=1, le=100, description="Max number of films to return"),
    db: DatabaseSession = Depends(get_db),
    trace_id: str = Depends(get_trace_id),
) -> list[FilmResponse]:
    """
    Retrieve all films with optional genre and validated year range filters.
    Performs real asynchronous database reads via handlers and services.
    """
    response.headers["X-Trace-Id"] = trace_id

    logger.info(
        f"[{trace_id}] list_films called | API {proj.API_VERSION} | "
        f"DB Session active={db.is_active}"
    )

    query = FilmFilterQuery(
        genre=genre,
        start_year=start_year,
        end_year=end_year,
        limit=limit,
    )
    return await film_handler.get_all_films(db=db, query=query)


@router.get("/{film_id}", response_model=FilmResponse, summary="Get film by ID")
async def get_film(
    film_id: int,
    response: Response,
    db: DatabaseSession = Depends(get_db),
    trace_id: str = Depends(get_trace_id),
) -> FilmResponse:
    """Retrieve a single film by ID using handler and service layer."""
    response.headers["X-Trace-Id"] = trace_id

    logger.info(
        f"[{trace_id}] get_film({film_id}) | API {proj.API_VERSION} | "
        f"DB Session active={db.is_active}"
    )
    return await film_handler.get_film_by_id(db=db, film_id=film_id)


@router.post("", response_model=FilmResponse, status_code=status.HTTP_201_CREATED, summary="Create a new film")
async def create_film(
    payload: FilmCreate,
    response: Response,
    db: DatabaseSession = Depends(get_db),
    trace_id: str = Depends(get_trace_id),
) -> FilmResponse:
    """Create a new film in PostgreSQL."""
    response.headers["X-Trace-Id"] = trace_id

    logger.info(
        f"[{trace_id}] create_film '{payload.title}' | API {proj.API_VERSION} | "
        f"DB active={db.is_active}"
    )
    return await film_handler.create_film(db=db, payload=payload)


@router.patch("/{film_id}", response_model=FilmResponse, summary="Partially update a film")
async def update_film(
    film_id: int,
    payload: FilmUpdate,
    response: Response,
    db: DatabaseSession = Depends(get_db),
    trace_id: str = Depends(get_trace_id),
) -> FilmResponse:
    """Partially update an existing film in PostgreSQL."""
    response.headers["X-Trace-Id"] = trace_id

    logger.info(f"[{trace_id}] update_film({film_id}) | DB active={db.is_active}")
    return await film_handler.update_film(db=db, film_id=film_id, payload=payload)


@router.delete("/{film_id}", response_model=MessageResponse, summary="Delete a film")
async def delete_film(
    film_id: int,
    response: Response,
    db: DatabaseSession = Depends(get_db),
    trace_id: str = Depends(get_trace_id),
) -> MessageResponse:
    """Delete a film by ID from PostgreSQL."""
    response.headers["X-Trace-Id"] = trace_id

    logger.info(f"[{trace_id}] delete_film({film_id}) | DB active={db.is_active}")
    return await film_handler.delete_film(db=db, film_id=film_id)
