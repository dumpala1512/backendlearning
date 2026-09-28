from fastapi import HTTPException, status
from app.models.review import RatingRangeFilter, ReviewCreate, ReviewResponse, ReviewUpdate
from app.models.common import MessageResponse
from app.services import review_service


def get_film_reviews(
    film_id: int,
    rating_filter: RatingRangeFilter | None = None,
) -> list[ReviewResponse]:
    """Get all reviews for a film or raise 404 if film doesn't exist."""
    min_rating = rating_filter.min_rating if rating_filter else None
    max_rating = rating_filter.max_rating if rating_filter else None

    reviews = review_service.get_film_reviews(
        film_id=film_id,
        min_rating=min_rating,
        max_rating=max_rating,
    )
    if reviews is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Film with id {film_id} not found",
        )
    return [ReviewResponse.model_validate(r) for r in reviews]


def create_review(film_id: int, payload: ReviewCreate) -> ReviewResponse:
    """Create a new review for a film or raise 404."""
    data = payload.model_dump()
    data["film_id"] = film_id
    review = review_service.add_review(**data)
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Film with id {film_id} not found",
        )
    return ReviewResponse.model_validate(review)


def update_review(review_id: int, payload: ReviewUpdate) -> ReviewResponse:
    """Update review rating or text using model_dump(exclude_unset=True)."""
    review = review_service.update_review(review_id, **payload.model_dump(exclude_unset=True))
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review with id {review_id} not found",
        )
    return ReviewResponse.model_validate(review)


def delete_review(review_id: int) -> MessageResponse:
    """Delete a review by ID."""
    if not review_service.delete_review(review_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review with id {review_id} not found",
        )
    return MessageResponse(message=f"Review {review_id} successfully deleted", success=True)
