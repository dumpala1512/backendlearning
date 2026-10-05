"""
Demonstration service showcasing Pydantic v2 Serialization:
- model_dump()
- model_dump_json()
- include
- exclude
- exclude_none
- exclude_unset
- exclude_defaults
"""
from typing import Any
from app.schemas.film import FilmResponse, FilmUpdate
import uuid


def demonstrate_serialization() -> dict[str, Any]:
    """
    Executes and returns examples of all Pydantic v2 serialization techniques.
    """
    # Create sample instance
    film = FilmResponse(
        id=uuid.uuid4(),
        title="Interstellar",
        director="Christopher Nolan",
        releaseYear=2014,
        genre="Sci-Fi",
        description="A team of explorers travel through a wormhole in space in an attempt to ensure humanity's survival.",
    )

    # 1. model_dump(): serializes the model to a native Python dictionary
    dump_full = film.model_dump()

    # 2. model_dump_json(): serializes the model directly into a valid JSON string
    dump_json = film.model_dump_json()

    # 3. include: selectively includes only specified fields in the serialization
    dump_include = film.model_dump(include={"id", "title", "release_year", "years_since_release"})

    # 4. exclude: selectively removes specified fields from the serialization
    dump_exclude = film.model_dump(exclude={"description", "created_at"})

    # Sample update model with unset fields and explicit None values
    update_model = FilmUpdate(
        title="Interstellar (IMAX Re-release)",
        director=None,
    )

    # 5. exclude_none: omits fields whose values are explicitly None
    dump_exclude_none = update_model.model_dump(exclude_none=True)

    # 6. exclude_unset: omits fields that were not explicitly passed when instantiating the model
    dump_exclude_unset = update_model.model_dump(exclude_unset=True)

    # Sample model with default values (description defaults to "")
    film_with_defaults = FilmResponse(
        id=uuid.uuid4(),
        title="Memento",
        director="Christopher Nolan",
        releaseYear=2000,
        genre="Mystery",
    )

    # 7. exclude_defaults: omits fields that still hold their schema-defined default values
    dump_exclude_defaults = film_with_defaults.model_dump(exclude_defaults=True)

    return {
        "model_dump": dump_full,
        "model_dump_json": dump_json,
        "include": dump_include,
        "exclude": dump_exclude,
        "exclude_none": dump_exclude_none,
        "exclude_unset": dump_exclude_unset,
        "exclude_defaults": dump_exclude_defaults,
    }
