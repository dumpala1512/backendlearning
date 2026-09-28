from fastapi import APIRouter, Query, status
from app.handlers import film_handler
from app.models.common import MessageResponse
from app.models.film import FilmCreate, FilmFilterQuery, FilmResponse, FilmUpdate

router = APIRouter(prefix="/films", tags=["Films"])


@router.get("", response_model=list[FilmResponse], summary="List all films")
def list_films(
    genre: str | None = Query(None, description="Filter films by genre"),
    start_year: int | None = Query(None, ge=1888, le=2100, description="Filter by minimum release year"),
    end_year: int | None = Query(None, ge=1888, le=2100, description="Filter by maximum release year"),
    limit: int = Query(10, ge=1, le=100, description="Max number of films to return"),
) -> list[FilmResponse]:
    """Retrieve all films with optional genre and validated year range filters."""
    query = FilmFilterQuery(
        genre=genre,
        start_year=start_year,
        end_year=end_year,
        limit=limit,
    )
    return film_handler.get_all_films(query=query)


@router.get("/{film_id}", response_model=FilmResponse, summary="Get film by ID")
def get_film(film_id: int) -> FilmResponse:
    """Retrieve a single film by its ID. Includes the computed years_since_release field."""
    return film_handler.get_film_by_id(film_id=film_id)


@router.post("", response_model=FilmResponse, status_code=status.HTTP_201_CREATED, summary="Create a new film")
def create_film(payload: FilmCreate) -> FilmResponse:
    """Create a new film using FilmCreate model (inherited from FilmBase). Supports alias 'releaseYear'."""
    return film_handler.create_film(payload=payload)


@router.patch("/{film_id}", response_model=FilmResponse, summary="Partially update a film")
def update_film(film_id: int, payload: FilmUpdate) -> FilmResponse:
    """Partially update an existing film. Uses model_dump(exclude_unset=True)."""
    return film_handler.update_film(film_id=film_id, payload=payload)


@router.delete("/{film_id}", response_model=MessageResponse, summary="Delete a film")
def delete_film(film_id: int) -> MessageResponse:
    """Delete a film by ID."""
    return film_handler.delete_film(film_id=film_id)
