from fastapi import APIRouter, HTTPException, Query, status
from app.handlers import review_handler
from app.models.common import MessageResponse
from app.models.review import RatingRangeFilter, ReviewCreate, ReviewResponse, ReviewUpdate

router = APIRouter(tags=["Reviews"])


@router.get(
    "/films/{film_id}/reviews",
    response_model=list[ReviewResponse],
    summary="Get reviews for a film",
)
def get_film_reviews(
    film_id: int,
    min_rating: int | None = Query(None, ge=1, le=10, description="Minimum rating filter"),
    max_rating: int | None = Query(None, ge=1, le=10, description="Maximum rating filter"),
) -> list[ReviewResponse]:
    """Retrieve all reviews for a specific film with optional rating range filtering."""
    rating_filter = None
    if min_rating is not None or max_rating is not None:
        rating_filter = RatingRangeFilter(
            min_rating=min_rating if min_rating is not None else 1,
            max_rating=max_rating if max_rating is not None else 10,
        )
    return review_handler.get_film_reviews(film_id=film_id, rating_filter=rating_filter)


@router.post(
    "/films/{film_id}/reviews",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a review for a film",
)
def create_review(film_id: int, payload: ReviewCreate) -> ReviewResponse:
    """Submit a review for a film. Enforces min 50 characters and integer rating [1, 10]."""
    if payload.film_id != film_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Route film_id ({film_id}) does not match body film_id ({payload.film_id})",
        )
    return review_handler.create_review(film_id=film_id, payload=payload)


@router.post(
    "/reviews",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a review",
)
def create_review_direct(payload: ReviewCreate) -> ReviewResponse:
    """Submit a review directly via ReviewCreate payload."""
    return review_handler.create_review(film_id=payload.film_id, payload=payload)


@router.patch(
    "/reviews/{review_id}",
    response_model=ReviewResponse,
    summary="Update a review",
)
def update_review(review_id: int, payload: ReviewUpdate) -> ReviewResponse:
    """Update rating or review body of an existing review."""
    return review_handler.update_review(review_id=review_id, payload=payload)


@router.delete(
    "/reviews/{review_id}",
    response_model=MessageResponse,
    summary="Delete a review",
)
def delete_review(review_id: int) -> MessageResponse:
    """Delete a review by its ID."""
    return review_handler.delete_review(review_id=review_id)
