from __future__ import annotations

import uuid
from typing import AsyncGenerator

from fastapi import Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, settings
from app.core.database import async_session_factory
from app.dao.film_dao import FilmDAO
from app.dao.review_dao import ReviewDAO
from app.dao.user_dao import UserDAO
from app.services.film_service import FilmService
from app.services.review_service import ReviewService
from app.services.user_service import UserService

# Backwards compatibility alias: DatabaseSession points to SQLAlchemy's AsyncSession
DatabaseSession = AsyncSession


def get_settings() -> Settings:
    """Provide the application Settings singleton."""
    return settings


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Provide an AsyncSession for each HTTP request.
    Yields the session using a dependency and automatically closes the session
    after the request completes (via the async context manager).
    """
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


def get_request_id(
    request: Request,
) -> str:
    """Retrieve active request ID from request state or generate a new UUID4."""
    return getattr(request.state, "request_id", None) or str(uuid.uuid4())


# Backward-compatibility alias
get_trace_id = get_request_id


# ---------------------------------------------------------------------------
# DAO Dependency Providers
# ---------------------------------------------------------------------------
def get_film_dao() -> FilmDAO:
    """Provide FilmDAO dependency."""
    return FilmDAO()


def get_review_dao() -> ReviewDAO:
    """Provide ReviewDAO dependency."""
    return ReviewDAO()


def get_user_dao() -> UserDAO:
    """Provide UserDAO dependency."""
    return UserDAO()


from app.core.security import decode_token
from app.dao.refresh_token_dao import RefreshTokenDAO, default_refresh_token_dao
from app.exceptions.user import AuthenticationError, InvalidTokenError
from app.schemas.user import AuthenticatedUser


def get_refresh_token_dao() -> RefreshTokenDAO:
    """Provide RefreshTokenDAO dependency."""
    return default_refresh_token_dao


# ---------------------------------------------------------------------------
# Service Dependency Providers
# ---------------------------------------------------------------------------
def get_film_service(
    dao: FilmDAO = Depends(get_film_dao),
    review_dao: ReviewDAO = Depends(get_review_dao),
) -> FilmService:
    """Provide FilmService with injected FilmDAO and ReviewDAO."""
    return FilmService(dao=dao, review_dao=review_dao)


def get_review_service(
    dao: ReviewDAO = Depends(get_review_dao),
    film_dao: FilmDAO = Depends(get_film_dao),
) -> ReviewService:
    """Provide ReviewService with injected ReviewDAO and FilmDAO."""
    return ReviewService(dao=dao, film_dao=film_dao)


def get_user_service(
    dao: UserDAO = Depends(get_user_dao),
    film_dao: FilmDAO = Depends(get_film_dao),
    review_dao: ReviewDAO = Depends(get_review_dao),
    refresh_token_dao: RefreshTokenDAO = Depends(get_refresh_token_dao),
) -> UserService:
    """Provide UserService with injected UserDAO, FilmDAO, ReviewDAO, and RefreshTokenDAO."""
    return UserService(
        dao=dao,
        film_dao=film_dao,
        review_dao=review_dao,
        refresh_token_dao=refresh_token_dao,
    )


from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

http_bearer = HTTPBearer(
    auto_error=False,
    description="Enter your JWT Access Token",
)


# ---------------------------------------------------------------------------
# Authentication Dependency
# ---------------------------------------------------------------------------
async def get_current_user(
    auth: HTTPAuthorizationCredentials | None = Depends(http_bearer),
    raw_auth: str | None = Header(None, alias="Authorization"),
) -> AuthenticatedUser:
    """
    Reusable FastAPI authentication dependency using HTTPBearer.
    - Enables Swagger UI 'Authorize' button with direct Access Token input
    - Renders lock icons (🔒) on all protected routes
    - Decodes the JWT and validates claims statelessly
    - Rejects unauthenticated requests with HTTP 401 Unauthorized
    """
    if not auth or not auth.credentials:
        if raw_auth and not raw_auth.lower().startswith("bearer "):
            raise AuthenticationError(message="Invalid authorization header format. Expected 'Bearer <token>'.")
        raise AuthenticationError(message="Authorization header is missing.")

    token = auth.credentials
    payload = decode_token(token, expected_type="access")

    sub = payload.get("sub")
    username = payload.get("username")
    role = payload.get("role", "user")

    if not sub or not username:
        raise InvalidTokenError(message="Token missing required user claims.")

    try:
        user_id = uuid.UUID(sub)
    except (ValueError, TypeError):
        raise InvalidTokenError(message="Invalid user ID format in token subject.")

    return AuthenticatedUser(
        id=user_id,
        username=username,
        role=role,
    )
