from __future__ import annotations

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
from app.exceptions.handlers import (
    EXCEPTION_STATUS_MAPPINGS,
    create_error_response,
    register_exception_handlers,
)
from app.exceptions.review import (
    InvalidReviewRatingError,
    ReviewAlreadyExistsError,
    ReviewNotFoundError,
    ReviewPermissionDeniedError,
)
from app.exceptions.user import (
    InvalidCredentialsError,
    InvalidTokenError,
    TokenExpiredError,
    TokenReusedError,
    TokenRevokedError,
    UserAlreadyExistsError,
    UserNotFoundError,
)

__all__ = [
    "AuthenticationError",
    "DomainError",
    "DuplicateEntityError",
    "EntityNotFoundError",
    "PermissionDeniedError",
    "ValidationError",
    "FilmNotFoundError",
    "FilmHasActiveReviewsError",
    "FilmAlreadyExistsError",
    "ReviewNotFoundError",
    "ReviewAlreadyExistsError",
    "ReviewPermissionDeniedError",
    "InvalidReviewRatingError",
    "UserNotFoundError",
    "UserAlreadyExistsError",
    "InvalidCredentialsError",
    "InvalidTokenError",
    "TokenExpiredError",
    "TokenReusedError",
    "TokenRevokedError",
    "EXCEPTION_STATUS_MAPPINGS",
    "create_error_response",
    "register_exception_handlers",
]

