from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dao import user_dao
from app.models.common import MessageResponse
from app.models.review import RatingRangeFilter, ReviewCreate, ReviewResponse, ReviewUpdate
from app.services import review_service


async def get_film_reviews(
    db: AsyncSession,
    film_id: int,
    rating_filter: RatingRangeFilter | None = None,
) -> list[ReviewResponse]:
    """Get all reviews for a film via review_service or raise 404 if film doesn't exist."""
    min_rating = rating_filter.min_rating if rating_filter else None
    max_rating = rating_filter.max_rating if rating_filter else None

    reviews = await review_service.get_film_reviews(
        db=db,
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


async def create_review(
    db: AsyncSession,
    film_id: int,
    payload: ReviewCreate,
) -> ReviewResponse:
    """Create a new review for a film via review_service or raise 404."""
    user_id = payload.user_id

    # If user_id is not explicitly passed in payload, resolve by reviewer_display_name
    if user_id is None and payload.reviewer_display_name:
        display_name = payload.reviewer_display_name.strip()
        if display_name.lower() != "anonymous critic":
            matched_user = await user_dao.get_by_username(db, display_name)
            if matched_user:
                user_id = matched_user.id

    review = await review_service.add_review(
        db=db,
        film_id=film_id,
        rating=payload.rating,
        review=payload.review,
        reviewer_display_name=payload.reviewer_display_name,
        user_id=user_id,
    )
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Film with id {film_id} not found",
        )
    return ReviewResponse.model_validate(review)


async def update_review(
    db: AsyncSession,
    review_id: int,
    payload: ReviewUpdate,
) -> ReviewResponse:
    """Update review rating or text via review_service or raise 404."""
    review = await review_service.update_review(
        db=db,
        review_id=review_id,
        **payload.model_dump(exclude_unset=True),
    )
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review with id {review_id} not found",
        )
    return ReviewResponse.model_validate(review)


async def delete_review(db: AsyncSession, review_id: int) -> MessageResponse:
    """Delete a review via review_service or raise 404."""
    deleted = await review_service.delete_review(db=db, review_id=review_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review with id {review_id} not found",
        )
    return MessageResponse(message=f"Review {review_id} successfully deleted", success=True)
