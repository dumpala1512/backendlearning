from fastapi import HTTPException, status
from app.schemas.film import FilmCreate, FilmResponse, FilmUpdate
from app.schemas.common import MessageResponse
from app.services import film_service


def get_all_films(genre: str | None = None, limit: int = 10) -> list[FilmResponse]:
    """Fetch films and convert them to response schemas."""
    films = film_service.list_films(genre=genre, limit=limit)
    return [
        FilmResponse(
            id=f.id,
            title=f.title,
            director=f.director,
            release_year=f.release_year,
            genre=f.genre,
            description=f.description,
            created_at=f.created_at,
        )
        for f in films
    ]


def get_film_by_id(film_id: int) -> FilmResponse:
    """Fetch a single film or raise 404."""
    film = film_service.get_film(film_id)
    if not film:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Film with id {film_id} not found",
        )
    return FilmResponse(
        id=film.id,
        title=film.title,
        director=film.director,
        release_year=film.release_year,
        genre=film.genre,
        description=film.description,
        created_at=film.created_at,
    )


def create_film(payload: FilmCreate) -> FilmResponse:
    """Create a new film and return it."""
    film = film_service.create_film(
        title=payload.title,
        director=payload.director,
        release_year=payload.release_year,
        genre=payload.genre,
        description=payload.description,
    )
    return FilmResponse(
        id=film.id,
        title=film.title,
        director=film.director,
        release_year=film.release_year,
        genre=film.genre,
        description=film.description,
        created_at=film.created_at,
    )


def update_film(film_id: int, payload: FilmUpdate) -> FilmResponse:
    """Update a film or raise 404."""
    updates = payload.model_dump(exclude_unset=True)
    film = film_service.update_film(film_id, **updates)
    if not film:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Film with id {film_id} not found",
        )
    return FilmResponse(
        id=film.id,
        title=film.title,
        director=film.director,
        release_year=film.release_year,
        genre=film.genre,
        description=film.description,
        created_at=film.created_at,
    )


def delete_film(film_id: int) -> MessageResponse:
    """Delete a film or raise 404."""
    success = film_service.delete_film(film_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Film with id {film_id} not found",
        )
    return MessageResponse(message=f"Film {film_id} successfully deleted", success=True)
