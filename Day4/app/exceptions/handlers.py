from __future__ import annotations

import logging
from typing import Any
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.exceptions.base import (
    AuthenticationError,
    DomainError,
    DuplicateEntityError,
    EntityNotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from app.exceptions.film import (
    FilmAlreadyExistsError,
    FilmHasActiveReviewsError,
    FilmNotFoundError,
)
from app.exceptions.review import (
    InvalidReviewRatingError,
    ReviewAlreadyExistsError,
    ReviewNotFoundError,
    ReviewPermissionDeniedError,
)
from app.exceptions.user import (
    InvalidCredentialsError,
    UserAlreadyExistsError,
    UserNotFoundError,
)

logger = logging.getLogger("app.exceptions")

EXCEPTION_STATUS_MAPPINGS: dict[type[DomainError], int] = {
    FilmNotFoundError: status.HTTP_404_NOT_FOUND,
    ReviewNotFoundError: status.HTTP_404_NOT_FOUND,
    UserNotFoundError: status.HTTP_404_NOT_FOUND,
    EntityNotFoundError: status.HTTP_404_NOT_FOUND,
    ReviewAlreadyExistsError: status.HTTP_409_CONFLICT,
    FilmHasActiveReviewsError: status.HTTP_409_CONFLICT,
    FilmAlreadyExistsError: status.HTTP_409_CONFLICT,
    UserAlreadyExistsError: status.HTTP_409_CONFLICT,
    DuplicateEntityError: status.HTTP_409_CONFLICT,
    ReviewPermissionDeniedError: status.HTTP_403_FORBIDDEN,
    PermissionDeniedError: status.HTTP_403_FORBIDDEN,
    InvalidCredentialsError: status.HTTP_401_UNAUTHORIZED,
    AuthenticationError: status.HTTP_401_UNAUTHORIZED,
    InvalidReviewRatingError: status.HTTP_400_BAD_REQUEST,
    ValidationError: status.HTTP_400_BAD_REQUEST,
}


def create_error_response(
    status_code: int,
    error_type: str,
    message: str,
    detail: Any = None,
) -> JSONResponse:
    """
    Build standardized JSON error response body.
    Includes explicit HTTP status code, machine-readable error type,
    clear human-readable message, and structured detail payload.
    """
    return JSONResponse(
        status_code=status_code,
        content={
            "status_code": status_code,
            "type": error_type,
            "message": message,
            "detail": detail if detail is not None else {},
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    """
    Centralized registration of domain exception handlers.
    Converts typed domain exceptions into standard JSON error responses.
    """

    @app.exception_handler(DomainError)
    async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
        # Resolve HTTP status code directly from exception instance or fallback mapping
        status_code: int = getattr(exc, "status_code", None) or EXCEPTION_STATUS_MAPPINGS.get(
            type(exc), status.HTTP_400_BAD_REQUEST
        )

        if status_code >= 500:
            logger.error(
                "Unhandled domain error [%d - %s]: %s",
                status_code,
                exc.error_type,
                exc.message,
                exc_info=True,
            )
        elif status_code in (
            status.HTTP_409_CONFLICT,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_401_UNAUTHORIZED,
        ):
            logger.warning(
                "Domain rule constraint triggered [%d - %s]: %s",
                status_code,
                exc.error_type,
                exc.message,
            )
        else:
            logger.info(
                "Domain error encountered [%d - %s]: %s",
                status_code,
                exc.error_type,
                exc.message,
            )

        return create_error_response(
            status_code=status_code,
            error_type=exc.error_type,
            message=exc.message,
            detail=exc.detail,
        )

