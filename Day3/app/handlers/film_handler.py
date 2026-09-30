from fastapi import HTTPException, status
from app.models.film import FilmCreate, FilmFilterQuery, FilmResponse, FilmUpdate
from app.models.common import MessageResponse
from app.services import film_service


def get_all_films(query: FilmFilterQuery | None = None) -> list[FilmResponse]:
    """Fetch films with optional filtering and convert to FilmResponse models."""
    genre = query.genre if query else None
    start_year = query.start_year if query else None
    end_year = query.end_year if query else None
    limit = query.limit if query else 10

    films = film_service.list_films(
        genre=genre,
        start_year=start_year,
        end_year=end_year,
        limit=limit,
    )
    return [FilmResponse.model_validate(f) for f in films]


def get_film_by_id(film_id: int) -> FilmResponse:
    """Fetch a single film or raise 404."""
    film = film_service.get_film(film_id)
    if not film:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Film with id {film_id} not found",
        )
    return FilmResponse.model_validate(film)


def create_film(payload: FilmCreate) -> FilmResponse:
    """Create a new film and return it using Pydantic model validation."""
    film = film_service.create_film(**payload.model_dump())
    return FilmResponse.model_validate(film)


def update_film(film_id: int, payload: FilmUpdate) -> FilmResponse:
    """Update a film using model_dump(exclude_unset=True) or raise 404."""
    film = film_service.update_film(film_id, **payload.model_dump(exclude_unset=True))
    if not film:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Film with id {film_id} not found",
        )
    return FilmResponse.model_validate(film)


def delete_film(film_id: int) -> MessageResponse:
    """Delete a film or raise 404."""
    if not film_service.delete_film(film_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Film with id {film_id} not found",
        )
    return MessageResponse(message=f"Film {film_id} successfully deleted", success=True)
