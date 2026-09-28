from app.models.review import Review

# Simple in-memory database for reviews
reviews_db: dict[int, Review] = {
    1: Review(
        id=1,
        film_id=1,
        rating=9,
        review="A breathtaking visual and narrative tour de force that keeps audiences hooked from the very first frame to the final credits.",
        reviewer_display_name="CinemaLover99",
    )
}

_next_id = 2


def get_by_film_id(film_id: int) -> list[Review]:
    """Get all reviews for a specific film."""
    return [r for r in reviews_db.values() if r.film_id == film_id]


def get_by_id(review_id: int) -> Review | None:
    """Find a review by its ID."""
    return reviews_db.get(review_id)


def create(film_id: int, rating: int, review: str, reviewer_display_name: str = "Anonymous Critic") -> Review:
    """Create and save a new review."""
    global _next_id
    new_review = Review(
        id=_next_id,
        film_id=film_id,
        rating=rating,
        review=review,
        reviewer_display_name=reviewer_display_name,
    )
    reviews_db[_next_id] = new_review
    _next_id += 1
    return new_review


def update(review_id: int, **fields) -> Review | None:
    """Update fields of an existing review."""
    rev = reviews_db.get(review_id)
    if not rev:
        return None
    for key, value in fields.items():
        if value is not None and hasattr(rev, key):
            setattr(rev, key, value)
    return rev


def delete(review_id: int) -> bool:
    """Delete a review by ID."""
    if review_id in reviews_db:
        del reviews_db[review_id]
        return True
    return False


def count() -> int:
    """Return total number of reviews."""
    return len(reviews_db)
