from __future__ import annotations

import uuid
from typing import Any, AsyncGenerator

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


from fastapi import Depends, Header, Request, status
from app.core.security import decode_token
from app.exceptions.base import PermissionDeniedError
from app.exceptions.user import AuthenticationError, InvalidTokenError
from app.schemas.user import AuthenticatedUser


from app.core.redis import get_redis_client
from app.services.redis_service import RedisService


def get_redis_service(
    client: Any = Depends(get_redis_client),
) -> RedisService:
    """Provide RedisService with injected shared Redis client singleton."""
    return RedisService(client=client)


# ---------------------------------------------------------------------------
# Service Dependency Providers
# ---------------------------------------------------------------------------
def get_film_service(
    dao: FilmDAO = Depends(get_film_dao),
    review_dao: ReviewDAO = Depends(get_review_dao),
    redis_service: RedisService = Depends(get_redis_service),
) -> FilmService:
    """Provide FilmService with injected FilmDAO, ReviewDAO, and RedisService."""
    return FilmService(dao=dao, review_dao=review_dao, redis_service=redis_service)


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
    redis_service: RedisService = Depends(get_redis_service),
) -> UserService:
    """Provide UserService with injected UserDAO, FilmDAO, ReviewDAO, and RedisService."""
    return UserService(
        dao=dao,
        film_dao=film_dao,
        review_dao=review_dao,
        redis_service=redis_service,
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


# ---------------------------------------------------------------------------
# Role Enforcement Dependencies (RBAC)
# ---------------------------------------------------------------------------
ROLE_HIERARCHY: dict[str, int] = {
    "viewer": 1,
    "critic": 2,
    "admin": 3,
}

# Compatibility aliases mapping legacy names to standard canonical roles
ROLE_ALIASES: dict[str, str] = {
    "user": "viewer",
    "member": "viewer",
}


class RoleChecker:
    """
    Role enforcement dependency that accepts a required role (or allowed roles)
    and raises an HTTP 403 Forbidden response (PermissionDeniedError)
    if the authenticated user's role does not satisfy it.
    """

    def __init__(self, *required_roles: str | list[str] | tuple[str, ...]) -> None:
        flat_roles: list[str] = []
        for r in required_roles:
            if isinstance(r, (list, tuple, set)):
                flat_roles.extend(r)
            else:
                flat_roles.append(r)
        self.required_roles = [r.strip().lower() for r in flat_roles]
        self.min_level = min(
            (ROLE_HIERARCHY.get(r, 1) for r in self.required_roles),
            default=1,
        )

    async def __call__(
        self,
        current_user: AuthenticatedUser = Depends(get_current_user),
    ) -> AuthenticatedUser:
        raw_role = (current_user.role or "").strip().lower()
        user_role = ROLE_ALIASES.get(raw_role, raw_role)
        user_level = ROLE_HIERARCHY.get(user_role, 1)

        satisfies = (
            user_role in self.required_roles
            or user_role == "admin"
            or user_level >= self.min_level
        )

        if not satisfies:
            req_str = ", ".join(self.required_roles)
            raise PermissionDeniedError(
                message=f"Access forbidden: role '{user_role}' does not satisfy required role '{req_str}'.",
                detail={
                    "user_role": user_role,
                    "required_roles": self.required_roles,
                },
                status_code=status.HTTP_403_FORBIDDEN,
            )
        return current_user


def require_role(*required_roles: str | list[str] | tuple[str, ...]) -> RoleChecker:
    """
    Factory function for role enforcement dependency.
    Accepts required role(s), e.g. require_role("admin"), require_role("critic"),
    or require_role(["critic", "admin"]).
    """
    return RoleChecker(*required_roles)

