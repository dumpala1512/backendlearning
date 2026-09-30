from datetime import datetime, timezone
from app.models.film import Film

# Simple in-memory database for films
films_db: dict[int, Film] = {
    1: Film(
        id=1,
        title="Inception",
        director="Christopher Nolan",
        release_year=2010,
        genre="Sci-Fi",
        description="A thief steals corporate secrets through dream-sharing technology.",
    ),
    2: Film(
        id=2,
        title="The Shawshank Redemption",
        director="Frank Darabont",
        release_year=1994,
        genre="Drama",
        description="Two convicts form a lasting friendship over the years.",
    ),
}

_next_id = 3


def get_all(genre: str | None = None, limit: int = 10) -> list[Film]:
    """Get all films, optionally filtered by genre."""
    results = list(films_db.values())
    if genre:
        results = [f for f in results if f.genre.lower() == genre.lower()]
    return results[:limit]


def get_by_id(film_id: int) -> Film | None:
    """Find a single film by its ID."""
    return films_db.get(film_id)


def create(title: str, director: str, release_year: int, genre: str, description: str = "") -> Film:
    """Add a new film to the database."""
    global _next_id
    new_film = Film(
        id=_next_id,
        title=title,
        director=director,
        release_year=release_year,
        genre=genre,
        description=description,
    )
    films_db[_next_id] = new_film
    _next_id += 1
    return new_film


def update(film_id: int, **fields) -> Film | None:
    """Update film details."""
    film = films_db.get(film_id)
    if not film:
        return None
    for key, value in fields.items():
        if value is not None and hasattr(film, key):
            setattr(film, key, value)
    return film


def delete(film_id: int) -> bool:
    """Delete a film by ID."""
    if film_id in films_db:
        del films_db[film_id]
        return True
    return False


def count() -> int:
    """Return total number of films."""
    return len(films_db)
