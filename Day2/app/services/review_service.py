from app.dao import film_dao, review_dao
from app.models.review import Review


def get_film_reviews(
    film_id: int,
    min_rating: int | None = None,
    max_rating: int | None = None,
) -> list[Review] | None:
    """Retrieve all reviews for a film, returning None if the film does not exist."""
    film = film_dao.get_by_id(film_id)
    if not film:
        return None
    reviews = review_dao.get_by_film_id(film_id)
    if min_rating is not None:
        reviews = [r for r in reviews if r.rating >= min_rating]
    if max_rating is not None:
        reviews = [r for r in reviews if r.rating <= max_rating]
    return reviews


def add_review(
    film_id: int,
    rating: int,
    review: str,
    reviewer_display_name: str = "Anonymous Critic",
) -> Review | None:
    """Add a review for a film. Returns None if the film does not exist."""
    film = film_dao.get_by_id(film_id)
    if not film:
        return None
    return review_dao.create(
        film_id=film_id,
        rating=rating,
        review=review.strip(),
        reviewer_display_name=reviewer_display_name.strip(),
    )


def update_review(review_id: int, **updates) -> Review | None:
    """Update fields of an existing review."""
    return review_dao.update(review_id, **updates)


def delete_review(review_id: int) -> bool:
    """Remove a review from the database."""
    return review_dao.delete(review_id)
