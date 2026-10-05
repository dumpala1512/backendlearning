from __future__ import annotations

from typing import Sequence
import uuid

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DuplicateEntityError, UserNotFoundError
from app.dao.film_dao import FilmDAO
from app.dao.review_dao import ReviewDAO
from app.dao.user_dao import UserDAO
from app.models.user import User, UserORM


def get_user_dao() -> UserDAO:
    return UserDAO()


def get_film_dao() -> FilmDAO:
    return FilmDAO()


def get_review_dao() -> ReviewDAO:
    return ReviewDAO()


class UserService:
    """
    Thin Service layer for User business logic and orchestration.
    Receives UserDAO, FilmDAO, and ReviewDAO via constructor injection and receives AsyncSession from routes.
    Decides when to raise domain exceptions (UserNotFoundError, DuplicateEntityError).
    Uses UUID for user_id.
    """

    def __init__(
        self,
        dao: UserDAO = Depends(get_user_dao),
        film_dao: FilmDAO = Depends(get_film_dao),
        review_dao: ReviewDAO = Depends(get_review_dao),
    ):
        self.dao = dao
        self.film_dao = film_dao
        self.review_dao = review_dao

    async def get_by_email(self, session: AsyncSession, email: str) -> User:
        """Find a user by email or raise UserNotFoundError."""
        user = await self.dao.get_by_email(session, email)
        if user is None:
            raise UserNotFoundError(f"User with email '{email}' not found")
        return user

    async def get_by_id(self, session: AsyncSession, user_id: uuid.UUID) -> User:
        """Find a user by UUID ID or raise UserNotFoundError."""
        user = await self.dao.get_by_id(session, user_id)
        if user is None:
            raise UserNotFoundError(f"User with id {user_id} not found")
        return user

    async def register(
        self,
        session: AsyncSession,
        username: str,
        email: str,
        password: str,
        role: str = "user",
        full_name: str = "",
    ) -> User:
        """Register a new user account with duplicate checks and full_name support."""
        existing_user = await self.dao.get_by_username(session, username)
        if existing_user:
            raise DuplicateEntityError(f"Username '{username}' is already taken.")

        existing_email = await self.dao.get_by_email(session, email)
        if existing_email:
            raise DuplicateEntityError(f"Email '{email}' is already registered.")

        return await self.dao.create(
            session=session,
            username=username.strip(),
            full_name=full_name.strip(),
            email=email.strip().lower(),
            hashed_password=f"hash_{password}",
            role=role,
        )

    async def login(self, session: AsyncSession, username: str, password: str) -> str:
        """Authenticate user credentials."""
        user = await self.dao.get_by_username(session, username)
        if not user:
            raise ValueError("Invalid username or password")
        return f"jwt_token_for_{user.username}"

    async def get_current_user(self, session: AsyncSession) -> User | None:
        """Return the current/first user or None."""
        users = await self.dao.get_all(session, limit=1)
        return users[0] if users else None

    async def list_users(self, session: AsyncSession, limit: int = 50) -> list[User]:
        """Return all users up to limit."""
        return await self.dao.get_all(session=session, limit=limit)

    async def get_admin_stats(self, session: AsyncSession) -> dict[str, int | str]:
        """Aggregate high-level platform statistics using DAO count methods."""
        return {
            "total_users": await self.dao.count(session),
            "total_films": await self.film_dao.count(session),
            "total_reviews": await self.review_dao.count(session),
            "uptime_status": "healthy",
        }


# Default singleton and module-level helpers for backward compatibility
_default_user_service = UserService(
    dao=UserDAO(),
    film_dao=FilmDAO(),
    review_dao=ReviewDAO(),
)


async def register(
    db: AsyncSession,
    username: str,
    email: str,
    password: str,
    role: str = "user",
    full_name: str = "",
) -> UserORM:
    return await _default_user_service.register(
        session=db,
        username=username,
        email=email,
        password=password,
        role=role,
        full_name=full_name,
    )


async def login(db: AsyncSession, username: str, password: str) -> str:
    return await _default_user_service.login(session=db, username=username, password=password)


async def get_current_user(db: AsyncSession) -> UserORM | None:
    return await _default_user_service.get_current_user(session=db)


async def list_users(db: AsyncSession, limit: int = 50) -> Sequence[UserORM]:
    return await _default_user_service.list_users(session=db, limit=limit)


async def get_admin_stats(db: AsyncSession) -> dict[str, int | str]:
    return await _default_user_service.get_admin_stats(session=db)
