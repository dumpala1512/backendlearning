from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence
import uuid

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.dao.film_dao import FilmDAO
from app.dao.refresh_token_dao import RefreshTokenDAO, default_refresh_token_dao
from app.dao.review_dao import ReviewDAO
from app.dao.user_dao import UserDAO
from app.exceptions import (
    DuplicateEntityError,
    InvalidCredentialsError,
    InvalidTokenError,
    TokenExpiredError,
    TokenReusedError,
    UserNotFoundError,
)
from app.models.user import User, UserORM


def get_user_dao() -> UserDAO:
    return UserDAO()


def get_film_dao() -> FilmDAO:
    return FilmDAO()


def get_review_dao() -> ReviewDAO:
    return ReviewDAO()


def get_refresh_token_dao() -> RefreshTokenDAO:
    return default_refresh_token_dao


class UserService:
    """
    Service layer for User business logic, credentials, and token management.
    Receives UserDAO, FilmDAO, ReviewDAO, and RefreshTokenDAO via constructor injection.
    """

    def __init__(
        self,
        dao: UserDAO = Depends(get_user_dao),
        film_dao: FilmDAO = Depends(get_film_dao),
        review_dao: ReviewDAO = Depends(get_review_dao),
        refresh_token_dao: RefreshTokenDAO = Depends(get_refresh_token_dao),
    ):
        self.dao = dao
        self.film_dao = film_dao
        self.review_dao = review_dao
        self.refresh_token_dao = refresh_token_dao

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
        """Register a new user account with duplicate checks and bcrypt password hashing."""
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
        Issues both an access token and a refresh token, recording the refresh token
        in the server-side database for replay prevention.
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
            raise InvalidCredentialsError(message="Invalid username or password credentials provided.")

        token_data = {
            "sub": str(user.id),
            "username": user.username,
            "role": user.role,
        }
        access_token = create_access_token(token_data)

        jti = str(uuid.uuid4())
        refresh_token = create_refresh_token(token_data, jti=jti)
        payload = decode_token(refresh_token, expected_type="refresh")
        expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)

        await self.refresh_token_dao.create(
            session=session,
            token=refresh_token,
            jti=jti,
            user_id=user.id,
            expires_at=expires_at,
        )
        return access_token, refresh_token, user

    async def refresh_access_token(
        self,
        session: AsyncSession,
        refresh_token: str,
    ) -> str:
        """
        Validate refresh token, reject expired or already-used tokens,
        mark the token as used, and issue a brand new access token.
        """
        payload = decode_token(refresh_token, expected_type="refresh")
        jti = payload.get("jti")
        user_id_str = payload.get("sub")
        if not jti or not user_id_str:
            raise InvalidTokenError(message="Refresh token is missing required claims.")

        record = await self.refresh_token_dao.get_by_jti(session, jti)
        if not record:
            record = await self.refresh_token_dao.get_by_token(session, refresh_token)
        if not record:
            raise InvalidTokenError(message="Invalid refresh token.")

        if record.is_used:
            raise TokenReusedError(message="Refresh token has already been used.")
        if record.is_revoked:
            raise TokenReusedError(message="Refresh token has been revoked.")

        expires_at = record.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if expires_at < datetime.now(timezone.utc):
            raise TokenExpiredError(message="Refresh token has expired.")

        # Mark refresh token as used (single use / replay protection)
        await self.refresh_token_dao.mark_as_used(session, record)

        user_id = uuid.UUID(user_id_str)
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
    refresh_token_dao=default_refresh_token_dao,
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
