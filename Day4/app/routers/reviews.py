from __future__ import annotations

import logging
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.core import proj
from app.dependencies import DatabaseSession, get_db, get_trace_id
from app.handlers import review_handler
from app.models.common import MessageResponse
from app.models.review import RatingRangeFilter, ReviewCreate, ReviewResponse, ReviewUpdate

logger = logging.getLogger("film_review.routers.reviews")

router = APIRouter(tags=["Reviews"])


@router.get(
    "/films/{film_id}/reviews",
    response_model=list[ReviewResponse],
    summary="Get reviews for a film",
)
async def get_film_reviews(
    film_id: int,
    response: Response,
    min_rating: int | None = Query(None, ge=1, le=10, description="Minimum rating filter"),
    max_rating: int | None = Query(None, ge=1, le=10, description="Maximum rating filter"),
    db: DatabaseSession = Depends(get_db),
    trace_id: str = Depends(get_trace_id),
) -> list[ReviewResponse]:
    """
    Retrieve all reviews for a specific film with optional rating range filtering.
    Performs real asynchronous database reads through handler and service layers.
    """
    response.headers["X-Trace-Id"] = trace_id

    logger.info(
        f"[{trace_id}] get_film_reviews(film_id={film_id}) | API {proj.API_VERSION} | "
        f"DB active={db.is_active}"
    )

    rating_filter = None
    if min_rating is not None or max_rating is not None:
        rating_filter = RatingRangeFilter(
            min_rating=min_rating if min_rating is not None else 1,
            max_rating=max_rating if max_rating is not None else 10,
        )

    return await review_handler.get_film_reviews(
        db=db,
        film_id=film_id,
        rating_filter=rating_filter,
    )


@router.post(
    "/films/{film_id}/reviews",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a review for a film",
)
async def create_review(
    film_id: int,
    payload: ReviewCreate,
    response: Response,
    db: DatabaseSession = Depends(get_db),
    trace_id: str = Depends(get_trace_id),
) -> ReviewResponse:
    """Submit a review for a film. Enforces min 50 characters and integer rating [1, 10]."""
    response.headers["X-Trace-Id"] = trace_id

    logger.info(
        f"[{trace_id}] create_review for film_id={film_id} | API {proj.API_VERSION} | "
        f"DB active={db.is_active}"
    )

    if payload.film_id != film_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Route film_id ({film_id}) does not match body film_id ({payload.film_id})",
        )

    return await review_handler.create_review(
        db=db,
        film_id=film_id,
        payload=payload,
    )


@router.post(
    "/reviews",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a review",
)
async def create_review_direct(
    payload: ReviewCreate,
    response: Response,
    db: DatabaseSession = Depends(get_db),
    trace_id: str = Depends(get_trace_id),
) -> ReviewResponse:
    """Submit a review directly via ReviewCreate payload."""
    response.headers["X-Trace-Id"] = trace_id

    logger.info(
        f"[{trace_id}] create_review_direct for film_id={payload.film_id} | "
        f"API {proj.API_VERSION} | DB active={db.is_active}"
    )

    return await review_handler.create_review(
        db=db,
        film_id=payload.film_id,
        payload=payload,
    )


@router.patch(
    "/reviews/{review_id}",
    response_model=ReviewResponse,
    summary="Update a review",
)
async def update_review(
    review_id: int,
    payload: ReviewUpdate,
    response: Response,
    db: DatabaseSession = Depends(get_db),
    trace_id: str = Depends(get_trace_id),
) -> ReviewResponse:
    """Update rating or review body of an existing review."""
    response.headers["X-Trace-Id"] = trace_id

    logger.info(f"[{trace_id}] update_review({review_id}) | DB active={db.is_active}")
    return await review_handler.update_review(
        db=db,
        review_id=review_id,
        payload=payload,
    )


@router.delete(
    "/reviews/{review_id}",
    response_model=MessageResponse,
    summary="Delete a review",
)
async def delete_review(
    review_id: int,
    response: Response,
    db: DatabaseSession = Depends(get_db),
    trace_id: str = Depends(get_trace_id),
) -> MessageResponse:
    """Delete a review by its ID."""
    response.headers["X-Trace-Id"] = trace_id

    logger.info(f"[{trace_id}] delete_review({review_id}) | DB active={db.is_active}")
    return await review_handler.delete_review(
        db=db,
        review_id=review_id,
    )
