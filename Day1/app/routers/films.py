from fastapi import APIRouter, Query, status
from app.handlers import film_handler
from app.schemas.common import MessageResponse
from app.schemas.film import FilmCreate, FilmResponse, FilmUpdate

router = APIRouter(prefix="/films", tags=["Films"])


@router.get("", response_model=list[FilmResponse], summary="List all films")
def list_films(
    genre: str | None = Query(None, description="Filter films by genre"),
    limit: int = Query(10, ge=1, le=100, description="Max number of films to return"),
) -> list[FilmResponse]:
    """Demonstrates Query parameters."""
    return film_handler.get_all_films(genre=genre, limit=limit)


@router.get("/{film_id}", response_model=FilmResponse, summary="Get film by ID")
def get_film(film_id: int) -> FilmResponse:
    """Demonstrates Path parameter."""
    return film_handler.get_film_by_id(film_id=film_id)


@router.post("", response_model=FilmResponse, status_code=status.HTTP_201_CREATED, summary="Create a new film")
def create_film(payload: FilmCreate) -> FilmResponse:
    """Demonstrates Request body."""
    return film_handler.create_film(payload=payload)


@router.patch("/{film_id}", response_model=FilmResponse, summary="Partially update a film")
def update_film(film_id: int, payload: FilmUpdate) -> FilmResponse:
    """Demonstrates Path parameter + Request body."""
    return film_handler.update_film(film_id=film_id, payload=payload)


@router.delete("/{film_id}", response_model=MessageResponse, summary="Delete a film")
def delete_film(film_id: int) -> MessageResponse:
    """Demonstrates Path parameter for deletion."""
    return film_handler.delete_film(film_id=film_id)
