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


def get_trace_id(
    request: Request,
) -> str:
    """Retrieve automatically generated trace ID from request state or generate a new UUID4."""
    return getattr(request.state, "trace_id", None) or str(uuid.uuid4())


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


# ---------------------------------------------------------------------------
# Service Dependency Providers
# ---------------------------------------------------------------------------
def get_film_service(
    dao: FilmDAO = Depends(get_film_dao),
) -> FilmService:
    """Provide FilmService with injected FilmDAO."""
    return FilmService(dao=dao)


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
) -> UserService:
    """Provide UserService with injected UserDAO, FilmDAO, and ReviewDAO."""
    return UserService(dao=dao, film_dao=film_dao, review_dao=review_dao)
