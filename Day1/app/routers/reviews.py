from fastapi import APIRouter, status
from app.handlers import review_handler
from app.schemas.common import MessageResponse
from app.schemas.review import ReviewCreate, ReviewResponse, ReviewUpdate

router = APIRouter(tags=["Reviews"])


@router.get("/films/{film_id}/reviews", response_model=list[ReviewResponse], summary="Get reviews for a film")
def get_film_reviews(film_id: int) -> list[ReviewResponse]:
    """Retrieve all reviews for a specific film."""
    return review_handler.get_film_reviews(film_id=film_id)


@router.post(
    "/films/{film_id}/reviews",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a review for a film",
)
def create_review(film_id: int, payload: ReviewCreate) -> ReviewResponse:
    """Submit a review for a film."""
    return review_handler.create_review(film_id=film_id, payload=payload)


@router.patch("/reviews/{review_id}", response_model=ReviewResponse, summary="Update a review")
def update_review(review_id: int, payload: ReviewUpdate) -> ReviewResponse:
    """Update rating or comment of an existing review."""
    return review_handler.update_review(review_id=review_id, payload=payload)


@router.delete("/reviews/{review_id}", response_model=MessageResponse, summary="Delete a review")
def delete_review(review_id: int) -> MessageResponse:
    """Delete a review by its ID."""
    return review_handler.delete_review(review_id=review_id)
