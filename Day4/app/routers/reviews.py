from __future__ import annotations

import logging
import uuid
from fastapi import APIRouter, Depends, Header, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import project_config
from app.dependencies import get_current_user, get_db, get_request_id, get_review_service
from app.exceptions.base import ValidationError
from app.schemas.common import MessageResponse
from app.schemas.review import RatingRangeFilter, ReviewCreate, ReviewResponse, ReviewUpdate
from app.schemas.user import AuthenticatedUser
from app.services.review_service import ReviewService

logger = logging.getLogger("film_review.routers.reviews")

router = APIRouter(tags=["Reviews"], dependencies=[Depends(get_current_user)])


@router.get(
    "/films/{film_id}/reviews",
    response_model=list[ReviewResponse],
    summary="Get reviews for a film",
)
async def get_film_reviews(
    film_id: uuid.UUID,
    min_rating: int | None = Query(None, ge=1, le=10, description="Minimum rating filter"),
    max_rating: int | None = Query(None, ge=1, le=10, description="Maximum rating filter"),
    service: ReviewService = Depends(get_review_service),
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id),
) -> list[ReviewResponse]:
    """
    Retrieve all reviews for a specific film with optional rating range filtering.
    Follows: Route -> Service -> DAO -> AsyncSession -> Database.
    """
    logger.info(
        f"[{request_id}] get_film_reviews(film_id={film_id}) | API {project_config.API_VERSION} | "
        f"DB active={db.is_active}"
    )

    if min_rating is not None or max_rating is not None:
        RatingRangeFilter(
            min_rating=min_rating if min_rating is not None else 1,
            max_rating=max_rating if max_rating is not None else 10,
        )

    reviews = await service.list_reviews(
        session=db,
        film_id=film_id,
        min_rating=min_rating,
        max_rating=max_rating,
    )
    return [ReviewResponse.model_validate(r) for r in reviews]


@router.get(
    "/films/{film_id}/reviews/average",
    summary="Get average rating for a film",
)
async def get_film_average_rating(
    film_id: uuid.UUID,
    service: ReviewService = Depends(get_review_service),
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id),
) -> dict[str, uuid.UUID | float | None]:
    """
    Calculate the average rating for a film.
    Follows: Route -> Service -> DAO -> AsyncSession -> Database.
    """
    avg = await service.average_rating(session=db, film_id=film_id)
    return {"film_id": film_id, "average_rating": avg}


@router.post(
    "/films/{film_id}/reviews",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a review for a film",
)
async def create_review(
    film_id: uuid.UUID,
    payload: ReviewCreate,
    service: ReviewService = Depends(get_review_service),
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id),
) -> ReviewResponse:
    """Submit a review for a film. Enforces min 50 characters and integer rating [1, 10]."""
    logger.info(
        f"[{request_id}] create_review for film_id={film_id} | API {project_config.API_VERSION} | "
        f"DB active={db.is_active}"
    )

    if payload.film_id != film_id:
        raise ValidationError(
            message=f"Route film_id ({film_id}) does not match body film_id ({payload.film_id})",
            detail={"film_id": str(film_id), "payload_film_id": str(payload.film_id)},
        )

    review = await service.add_review(
        session=db,
        film_id=film_id,
        rating=payload.rating,
        review=payload.review,
        reviewer_display_name=payload.reviewer_display_name,
        user_id=payload.user_id,
    )
    return ReviewResponse.model_validate(review)


@router.post(
    "/reviews",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a review",
)
async def create_review_direct(
    payload: ReviewCreate,
    service: ReviewService = Depends(get_review_service),
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id),
) -> ReviewResponse:
    """Submit a review directly via ReviewCreate payload."""
    logger.info(
        f"[{request_id}] create_review_direct for film_id={payload.film_id} | "
        f"API {project_config.API_VERSION} | DB active={db.is_active}"
    )

    review = await service.add_review(
        session=db,
        film_id=payload.film_id,
        rating=payload.rating,
        review=payload.review,
        reviewer_display_name=payload.reviewer_display_name,
        user_id=payload.user_id,
    )
    return ReviewResponse.model_validate(review)


@router.patch(
    "/reviews/{review_id}",
    response_model=ReviewResponse,
    summary="Update a review",
)
async def update_review(
    review_id: uuid.UUID,
    payload: ReviewUpdate,
    x_user_id: uuid.UUID | None = Header(None, alias="X-User-Id"),
    service: ReviewService = Depends(get_review_service),
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id),
) -> ReviewResponse:
    """Update rating or review body of an existing review with author validation."""
    logger.info(f"[{request_id}] update_review({review_id}) | DB active={db.is_active}")
    effective_user_id = payload.user_id or x_user_id
    updates = payload.model_dump(exclude_unset=True)
    updates.pop("user_id", None)
    review = await service.update_review(
        session=db,
        review_id=review_id,
        user_id=effective_user_id,
        **updates,
    )
    return ReviewResponse.model_validate(review)


@router.delete(
    "/reviews/{review_id}",
    response_model=MessageResponse,
    summary="Delete a review",
)
async def delete_review(
    review_id: uuid.UUID,
    service: ReviewService = Depends(get_review_service),
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id),
) -> MessageResponse:
    """Delete a review by its UUID ID."""
    logger.info(f"[{request_id}] delete_review({review_id}) | DB active={db.is_active}")
    await service.delete_review(session=db, review_id=review_id)
    return MessageResponse(message=f"Review {review_id} successfully deleted", success=True)
