from __future__ import annotations

import logging
import uuid
from fastapi import APIRouter, Depends, Header, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import project_config
from app.dependencies import (
    get_current_user,
    get_db,
    get_request_id,
    get_review_service,
    require_role,
)
from app.exceptions.base import PermissionDeniedError, ValidationError
from app.exceptions.review import ReviewPermissionDeniedError
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
    dependencies=[Depends(get_current_user), Depends(require_role("critic"))],
)
async def create_review(
    film_id: uuid.UUID,
    payload: ReviewCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: ReviewService = Depends(get_review_service),
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id),
) -> ReviewResponse:
    """Submit a review for a film (Critics and Admins only)."""
    logger.info(
        f"[{request_id}] create_review for film_id={film_id} | user={current_user.username} | "
        f"DB active={db.is_active}"
    )

    if payload.film_id != film_id:
        raise ValidationError(
            message=f"Route film_id ({film_id}) does not match body film_id ({payload.film_id})",
            detail={"film_id": str(film_id), "payload_film_id": str(payload.film_id)},
        )

    # Route-layer RBAC: Critics can only create reviews under their own identity
    author_id = payload.user_id
    if current_user.role != "admin" and payload.user_id is not None and payload.user_id != current_user.id:
        raise PermissionDeniedError(
            message="Critics can only create reviews under their own user identity.",
            detail={"user_id": str(current_user.id), "payload_user_id": str(payload.user_id)},
            status_code=status.HTTP_403_FORBIDDEN,
        )

    review = await service.add_review(
        session=db,
        film_id=film_id,
        rating=payload.rating,
        review=payload.review,
        reviewer_display_name=payload.reviewer_display_name,
        user_id=author_id,
    )
    return ReviewResponse.model_validate(review)


@router.post(
    "/reviews",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a review",
    dependencies=[Depends(get_current_user), Depends(require_role("critic"))],
)
async def create_review_direct(
    payload: ReviewCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: ReviewService = Depends(get_review_service),
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id),
) -> ReviewResponse:
    """Submit a review directly via ReviewCreate payload (Critics and Admins only)."""
    logger.info(
        f"[{request_id}] create_review_direct for film_id={payload.film_id} | "
        f"user={current_user.username} | DB active={db.is_active}"
    )

    # Route-layer RBAC: Critics can only create reviews under their own identity
    author_id = payload.user_id
    if current_user.role != "admin" and payload.user_id is not None and payload.user_id != current_user.id:
        raise PermissionDeniedError(
            message="Critics can only create reviews under their own user identity.",
            detail={"user_id": str(current_user.id), "payload_user_id": str(payload.user_id)},
            status_code=status.HTTP_403_FORBIDDEN,
        )

    review = await service.add_review(
        session=db,
        film_id=payload.film_id,
        rating=payload.rating,
        review=payload.review,
        reviewer_display_name=payload.reviewer_display_name,
        user_id=author_id,
    )
    return ReviewResponse.model_validate(review)


@router.patch(
    "/reviews/{review_id}",
    response_model=ReviewResponse,
    summary="Update a review",
    dependencies=[Depends(get_current_user), Depends(require_role("critic"))],
)
async def update_review(
    review_id: uuid.UUID,
    payload: ReviewUpdate,
    x_user_id: uuid.UUID | None = Header(None, alias="X-User-Id"),
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: ReviewService = Depends(get_review_service),
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id),
) -> ReviewResponse:
    """Update rating or review body (Admins can update any review; Critics only their own)."""
    logger.info(f"[{request_id}] update_review({review_id}) | user={current_user.username}")
    is_admin = current_user.role == "admin"
    effective_user_id = payload.user_id or x_user_id or current_user.id

    if not is_admin:
        existing_review = await service.get_by_id(session=db, review_id=review_id)
        if existing_review.user_id is not None and existing_review.user_id != current_user.id:
            raise ReviewPermissionDeniedError(
                review_id=review_id,
                user_id=effective_user_id,
                message="Only the original author may update this review.",
            )

    updates = payload.model_dump(exclude_unset=True)
    updates.pop("user_id", None)
    review = await service.update_review(
        session=db,
        review_id=review_id,
        user_id=effective_user_id,
        is_admin=is_admin,
        **updates,
    )
    return ReviewResponse.model_validate(review)


@router.delete(
    "/reviews/{review_id}",
    response_model=MessageResponse,
    summary="Delete a review",
    dependencies=[Depends(get_current_user), Depends(require_role("critic"))],
)
async def delete_review(
    review_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: ReviewService = Depends(get_review_service),
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id),
) -> MessageResponse:
    """Delete a review (Admins can delete any review; Critics only their own)."""
    logger.info(f"[{request_id}] delete_review({review_id}) | user={current_user.username}")
    is_admin = current_user.role == "admin"

    if not is_admin:
        existing_review = await service.get_by_id(session=db, review_id=review_id)
        if existing_review.user_id is not None and existing_review.user_id != current_user.id:
            raise ReviewPermissionDeniedError(
                review_id=review_id,
                user_id=current_user.id,
                message="Critics may only delete their own reviews.",
            )

    await service.delete_review(session=db, review_id=review_id)
    return MessageResponse(message=f"Review {review_id} successfully deleted", success=True)
