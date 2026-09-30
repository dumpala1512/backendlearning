import logging
from fastapi import APIRouter, Depends, Query, Response, status

from app.core.config import Settings
from app.dependencies import DatabaseSession, get_db, get_settings, get_trace_id
from app.handlers import film_handler
from app.models.common import MessageResponse
from app.models.film import FilmCreate, FilmFilterQuery, FilmResponse, FilmUpdate

logger = logging.getLogger("film_review.routers.films")

router = APIRouter(prefix="/films", tags=["Films"])


@router.get("", response_model=list[FilmResponse], summary="List all films")
def list_films(
    response: Response,
    genre: str | None = Query(None, description="Filter films by genre"),
    start_year: int | None = Query(None, ge=1888, le=2100, description="Filter by minimum release year"),
    end_year: int | None = Query(None, ge=1888, le=2100, description="Filter by maximum release year"),
    limit: int = Query(10, ge=1, le=100, description="Max number of films to return"),
    settings: Settings = Depends(get_settings),
    db: DatabaseSession = Depends(get_db),
    trace_id: str = Depends(get_trace_id),
) -> list[FilmResponse]:
    """
    Retrieve all films with optional genre and validated year range filters.

    Demonstrates FastAPI Dependency Injection:
    - settings: injected via get_settings (API v{settings.API_VERSION})
    - db: injected via get_db (session active={db.is_active})
    - trace_id: injected via get_trace_id (client or generated UUID)
    """
    response.headers["X-Trace-Id"] = trace_id

    logger.info(
        f"[{trace_id}] list_films called | API {settings.API_VERSION} | "
        f"DB Session {db.session_id} active={db.is_active}"
    )

    query = FilmFilterQuery(
        genre=genre,
        start_year=start_year,
        end_year=end_year,
        limit=limit,
    )
    return film_handler.get_all_films(query=query)


@router.get("/{film_id}", response_model=FilmResponse, summary="Get film by ID")
def get_film(
    film_id: int,
    response: Response,
    settings: Settings = Depends(get_settings),
    db: DatabaseSession = Depends(get_db),
    trace_id: str = Depends(get_trace_id),
) -> FilmResponse:
    """
    Retrieve a single film by its ID. Includes the computed years_since_release field.

    Demonstrates FastAPI Dependency Injection:
    - settings: injected via get_settings
    - db: injected via get_db
    - trace_id: injected via get_trace_id
    """
    response.headers["X-Trace-Id"] = trace_id

    logger.info(
        f"[{trace_id}] get_film({film_id}) | API {settings.API_VERSION} | "
        f"DB Session {db.session_id} active={db.is_active}"
    )
    return film_handler.get_film_by_id(film_id=film_id)


@router.post("", response_model=FilmResponse, status_code=status.HTTP_201_CREATED, summary="Create a new film")
def create_film(
    payload: FilmCreate,
    response: Response,
    settings: Settings = Depends(get_settings),
    db: DatabaseSession = Depends(get_db),
    trace_id: str = Depends(get_trace_id),
) -> FilmResponse:
    """
    Create a new film using FilmCreate model. Supports alias 'releaseYear'.

    Demonstrates FastAPI Dependency Injection:
    - settings: injected via get_settings
    - db: injected via get_db
    - trace_id: injected via get_trace_id
    """
    response.headers["X-Trace-Id"] = trace_id

    logger.info(
        f"[{trace_id}] create_film '{payload.title}' | API {settings.API_VERSION} | "
        f"DB Session {db.session_id}"
    )
    return film_handler.create_film(payload=payload)


@router.patch("/{film_id}", response_model=FilmResponse, summary="Partially update a film")
def update_film(
    film_id: int,
    payload: FilmUpdate,
    response: Response,
    settings: Settings = Depends(get_settings),
    db: DatabaseSession = Depends(get_db),
    trace_id: str = Depends(get_trace_id),
) -> FilmResponse:
    """Partially update an existing film. Uses model_dump(exclude_unset=True)."""
    response.headers["X-Trace-Id"] = trace_id

    logger.info(f"[{trace_id}] update_film({film_id}) | DB Session {db.session_id}")
    return film_handler.update_film(film_id=film_id, payload=payload)


@router.delete("/{film_id}", response_model=MessageResponse, summary="Delete a film")
def delete_film(
    film_id: int,
    response: Response,
    settings: Settings = Depends(get_settings),
    db: DatabaseSession = Depends(get_db),
    trace_id: str = Depends(get_trace_id),
) -> MessageResponse:
    """Delete a film by ID."""
    response.headers["X-Trace-Id"] = trace_id

    logger.info(f"[{trace_id}] delete_film({film_id}) | DB Session {db.session_id}")
    return film_handler.delete_film(film_id=film_id)
