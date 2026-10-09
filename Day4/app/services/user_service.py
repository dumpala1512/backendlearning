from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Sequence
import uuid

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.dao.film_dao import FilmDAO
from app.dao.review_dao import ReviewDAO
from app.dao.user_dao import UserDAO
from app.exceptions import (
    DuplicateEntityError,
    InvalidCredentialsError,
    InvalidTokenError,
    PermissionDeniedError,
    TokenExpiredError,
    TokenReusedError,
    TokenRevokedError,
    UserNotFoundError,
)
from app.models.user import User, UserORM
from app.services.redis_service import RedisService


def get_user_dao() -> UserDAO:
    return UserDAO()


def get_film_dao() -> FilmDAO:
    return FilmDAO()


def get_review_dao() -> ReviewDAO:
    return ReviewDAO()


logger = logging.getLogger("film_review.services.user")


class UserService:
    """
    Service layer for User business logic, credentials, and token management.
    Receives UserDAO, FilmDAO, ReviewDAO, and RedisService via constructor injection.
    """

    def __init__(
        self,
        dao: UserDAO = Depends(get_user_dao),
        film_dao: FilmDAO = Depends(get_film_dao),
        review_dao: ReviewDAO = Depends(get_review_dao),
        refresh_token_dao: Any = None,
        redis_service: RedisService | None = None,
    ):
        self.dao = dao
        self.film_dao = film_dao
        self.review_dao = review_dao
        self.redis_service = redis_service

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
        role: str = "viewer",
        full_name: str = "",
    ) -> User:
        """Register a new user account with duplicate checks and bcrypt password hashing."""
        if full_name is None:
            raise ValueError("Full name cannot be null.")

        if role.strip().lower() == "admin":
            raise PermissionDeniedError(
                "Creating admin accounts via registration is prohibited. "
                "Only one system administrator account exists."
            )

        existing_user = await self.dao.get_by_username(session, username)
        if existing_user:
            raise DuplicateEntityError(f"Username '{username}' is already taken.")

        existing_email = await self.dao.get_by_email(session, email)
        if existing_email:
            raise DuplicateEntityError(f"Email '{email}' is already registered.")

        # Hash password securely using passlib + bcrypt
        hashed_password = hash_password(password)

        return await self.dao.create(
            session=session,
            username=username.strip(),
            full_name=full_name.strip(),
            email=email.strip().lower(),
            hashed_password=hashed_password,
            role=role,
        )

    async def login(
        self,
        session: AsyncSession,
        username: str | None = None,
        password: str = "",
        email: str | None = None,
    ) -> tuple[str, str, User]:
        """
        Authenticate user credentials by username or email.
        Issues an access token and a refresh token, recording the refresh token
        in Redis with TTL matching the JWT expiration.
        """
        user = None
        if username:
            user = await self.dao.get_by_username(session, username)
            if not user and "@" in username:
                user = await self.dao.get_by_email(session, username)
        if not user and email:
            user = await self.dao.get_by_email(session, email)
            if not user and "@" not in email:
                user = await self.dao.get_by_username(session, email)

        if not user or not verify_password(password, user.hashed_password):
            logger.warning(f"Failed login attempt for identifier='{username or email}'")
            raise InvalidCredentialsError(message="Invalid username or password credentials provided.")

        token_data = {
            "sub": str(user.id),
            "username": user.username,
            "role": user.role,
        }
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)

        # Store refresh token in Redis with TTL = refresh token expiry
        if not self.redis_service:
            logger.warning(
                "Redis service is unavailable; skipping storing refresh token for user %s",
                user.id,
            )
        else:
            try:
                ttl = settings.refresh_token_ttl_seconds
                await self.redis_service.set(
                    f"refresh_token:{refresh_token}",
                    str(user.id),
                    ttl=ttl,
                )
                # Track user's active refresh tokens for revocation during logout
                user_key = f"user_refresh_tokens:{user.id}"
                existing = await self.redis_service.get(user_key)
                tokens_list = existing if isinstance(existing, list) else ([existing] if existing else [])
                tokens_list.append(refresh_token)
                await self.redis_service.set(user_key, tokens_list, ttl=ttl)

                logger.info(f"Stored refresh token for user {user.id}")
            except Exception as exc:
                logger.error(
                    "Error storing refresh token in Redis for user %s: %s",
                    user.id,
                    exc,
                )

        return access_token, refresh_token, user

    async def refresh_access_token(
        self,
        session: AsyncSession,
        refresh_token: str,
    ) -> str:
        """
        Validate refresh token:
        1. JWT signature
        2. JWT expiry
        3. Token still exists in Redis
        If Redis lookup fails, returns HTTP 401 with 'Refresh token has been revoked'.
        """
        payload = decode_token(refresh_token, expected_type="refresh")
        user_id_str = payload.get("sub")
        if not user_id_str:
            raise InvalidTokenError(message="Refresh token is missing required claims.")

        try:
            user_id = uuid.UUID(user_id_str)
        except (ValueError, TypeError):
            raise InvalidTokenError(message="Invalid user ID format in token subject.")

        # Redis verification: ensure token is active and not revoked/logged out
        if self.redis_service:
            token_entry = await self.redis_service.get(f"refresh_token:{refresh_token}")
            if not token_entry:
                logger.warning(f"Refresh rejected: refresh token for user {user_id} has been revoked or expired in Redis")
                raise TokenRevokedError(message="Refresh token has been revoked", detail="Refresh token has been revoked")

        user = await self.dao.get_by_id(session, user_id)
        if not user:
            raise UserNotFoundError(user_id=user_id)

        return create_access_token(
            data={
                "sub": str(user.id),
                "username": user.username,
                "role": user.role,
            }
        )

    async def logout(self, user_id: uuid.UUID) -> None:
        """
        Revoke the user's refresh token(s) from Redis.
        Ensures deleted refresh tokens cannot be used to refresh access tokens.
        """
        if not self.redis_service:
            logger.warning(
                "Redis service is unavailable; cannot revoke refresh tokens for user %s",
                user_id,
            )
            return

        try:
            user_key = f"user_refresh_tokens:{user_id}"
            tokens = await self.redis_service.get(user_key)
            if tokens:
                if isinstance(tokens, list):
                    for token in tokens:
                        await self.redis_service.delete(f"refresh_token:{token}")
                    logger.info(f"Revoked refresh token for user {user_id}")
                else:
                    await self.redis_service.delete(f"refresh_token:{tokens}")
                await self.redis_service.delete(user_key)

            logger.info("Revoked refresh token for user %s", user_id)
        except Exception as exc:
            logger.error(
                "Error revoking refresh tokens from Redis for user %s: %s",
                user_id,
                exc,
            )

    async def get_current_user(self, session: AsyncSession) -> User | None:
        """Return the current/first user or None."""
        users = await self.dao.get_all(session, limit=1)
        return users[0] if users else None

    async def list_users(self, session: AsyncSession, limit: int = 50) -> list[User]:
        """Return all users up to limit."""
        return await self.dao.get_all(session=session, limit=limit)

    async def get_admin_stats(self, session: AsyncSession) -> dict[str, Any]:
        """Aggregate platform-wide statistics using DAO methods."""
        total_films = await self.film_dao.count(session)
        total_reviews = await self.review_dao.count(session)
        avg_rating = await self.review_dao.overall_average_rating(session)
        top_reviewer = await self.review_dao.get_top_reviewer(session)
        total_users = await self.dao.count(session)
        return {
            "total_users": total_users,
            "total_films": total_films,
            "total_reviews": total_reviews,
            "overall_average_rating": avg_rating,
            "top_reviewer_username": top_reviewer,
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


async def login(
    db: AsyncSession,
    username: str | None = None,
    password: str = "",
    email: str | None = None,
) -> tuple[str, str, UserORM]:
    return await _default_user_service.login(
        session=db,
        username=username,
        password=password,
        email=email,
    )


async def get_current_user(db: AsyncSession) -> UserORM | None:
    return await _default_user_service.get_current_user(session=db)


async def list_users(db: AsyncSession, limit: int = 50) -> Sequence[UserORM]:
    return await _default_user_service.list_users(session=db, limit=limit)


async def get_admin_stats(db: AsyncSession) -> dict[str, int | str]:
    return await _default_user_service.get_admin_stats(session=db)
