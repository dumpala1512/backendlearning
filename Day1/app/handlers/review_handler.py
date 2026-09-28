from fastapi import HTTPException, status
from app.schemas.review import ReviewCreate, ReviewResponse, ReviewUpdate
from app.schemas.common import MessageResponse
from app.services import review_service


def get_film_reviews(film_id: int) -> list[ReviewResponse]:
    """Get all reviews for a film or raise 404 if film doesn't exist."""
    reviews = review_service.get_film_reviews(film_id)
    if reviews is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Film with id {film_id} not found",
        )
    return [
        ReviewResponse(
            id=r.id,
            film_id=r.film_id,
            user_id=r.user_id,
            rating=r.rating,
            comment=r.comment,
            created_at=r.created_at,
        )
        for r in reviews
    ]


def create_review(film_id: int, payload: ReviewCreate) -> ReviewResponse:
    """Create a new review for a film or raise 404."""
    review = review_service.add_review(
        film_id=film_id,
        user_id=payload.user_id,
        rating=payload.rating,
        comment=payload.comment,
    )
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Film with id {film_id} not found",
        )
    return ReviewResponse(
        id=review.id,
        film_id=review.film_id,
        user_id=review.user_id,
        rating=review.rating,
        comment=review.comment,
        created_at=review.created_at,
    )


def update_review(review_id: int, payload: ReviewUpdate) -> ReviewResponse:
    """Update review rating or comment."""
    updates = payload.model_dump(exclude_unset=True)
    review = review_service.update_review(review_id, **updates)
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review with id {review_id} not found",
        )
    return ReviewResponse(
        id=review.id,
        film_id=review.film_id,
        user_id=review.user_id,
        rating=review.rating,
        comment=review.comment,
        created_at=review.created_at,
    )


def delete_review(review_id: int) -> MessageResponse:
    """Delete a review by ID."""
    success = review_service.delete_review(review_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review with id {review_id} not found",
        )
    return MessageResponse(message=f"Review {review_id} successfully deleted", success=True)
