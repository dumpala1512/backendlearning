from app.dao import film_dao
from app.models.film import Film


def list_films(
    genre: str | None = None,
    start_year: int | None = None,
    end_year: int | None = None,
    limit: int = 10,
) -> list[Film]:
    """Retrieve films from the database with optional genre and year range filters."""
    results = film_dao.get_all(genre=genre, limit=100)
    if start_year is not None:
        results = [f for f in results if f.release_year >= start_year]
    if end_year is not None:
        results = [f for f in results if f.release_year <= end_year]
    return results[:limit]


def get_film(film_id: int) -> Film | None:
    """Retrieve a single film by ID."""
    return film_dao.get_by_id(film_id)


def create_film(
    title: str,
    director: str,
    release_year: int,
    genre: str,
    description: str = "",
) -> Film:
    """Validate and create a new film."""
    return film_dao.create(
        title=title.strip(),
        director=director.strip(),
        release_year=release_year,
        genre=genre.strip(),
        description=description.strip(),
    )


def update_film(film_id: int, **updates) -> Film | None:
    """Update existing film details."""
    return film_dao.update(film_id, **updates)


def delete_film(film_id: int) -> bool:
    """Remove a film from the database."""
    return film_dao.delete(film_id)
