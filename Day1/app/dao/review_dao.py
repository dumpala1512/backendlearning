from app.models.review import Review

# Simple in-memory database for reviews
reviews_db: dict[int, Review] = {
    1: Review(
        id=1,
        film_id=1,
        user_id=1,
        rating=5,
        comment="Mind-bending cinematic masterpiece!",
    )
}

_next_id = 2


def get_by_film_id(film_id: int) -> list[Review]:
    """Get all reviews for a specific film."""
    return [r for r in reviews_db.values() if r.film_id == film_id]


def get_by_id(review_id: int) -> Review | None:
    """Find a review by its ID."""
    return reviews_db.get(review_id)


def create(film_id: int, user_id: int, rating: int, comment: str) -> Review:
    """Create and save a new review."""
    global _next_id
    new_review = Review(
        id=_next_id,
        film_id=film_id,
        user_id=user_id,
        rating=rating,
        comment=comment,
    )
    reviews_db[_next_id] = new_review
    _next_id += 1
    return new_review


def update(review_id: int, **fields) -> Review | None:
    """Update fields of an existing review."""
    review = reviews_db.get(review_id)
    if not review:
        return None
    for key, value in fields.items():
        if value is not None and hasattr(review, key):
            setattr(review, key, value)
    return review


def delete(review_id: int) -> bool:
    """Delete a review by ID."""
    if review_id in reviews_db:
        del reviews_db[review_id]
        return True
    return False


def count() -> int:
    """Return total number of reviews."""
    return len(reviews_db)
