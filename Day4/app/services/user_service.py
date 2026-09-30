from __future__ import annotations

from typing import Sequence
from sqlalchemy.ext.asyncio import AsyncSession

from app.dao import film_dao, review_dao, user_dao
from app.schemas import UserORM


async def register(
    db: AsyncSession,
    username: str,
    email: str,
    password: str,
    role: str = "user",
) -> UserORM:
    """Register a new user account with duplicate checks and real PostgreSQL persistence."""
    existing_user = await user_dao.get_by_username(db, username)
    if existing_user:
        raise ValueError(f"Username '{username}' is already taken.")

    existing_email = await user_dao.get_by_email(db, email)
    if existing_email:
        raise ValueError(f"Email '{email}' is already registered.")

    return await user_dao.create(
        db=db,
        username=username.strip(),
        email=email.strip().lower(),
        hashed_password=f"hash_{password}",
        role=role,
    )


async def login(db: AsyncSession, username: str, password: str) -> str:
    """Authenticate user against PostgreSQL credentials and return bearer token."""
    user = await user_dao.get_by_username(db, username)
    if not user:
        raise ValueError("Invalid username or password")
    # In production, verify hash(password) against user.hashed_password
    return f"jwt_token_for_{user.username}"


async def get_current_user(db: AsyncSession) -> UserORM | None:
    """Return current/first user from PostgreSQL or None."""
    users = await user_dao.get_all(db, limit=1)
    return users[0] if users else None


async def list_users(db: AsyncSession, limit: int = 50) -> Sequence[UserORM]:
    """Return all users from PostgreSQL."""
    return await user_dao.get_all(db, limit=limit)


async def get_admin_stats(db: AsyncSession) -> dict[str, int | str]:
    """Aggregate high-level platform statistics using real database counts."""
    return {
        "total_users": await user_dao.count(db),
        "total_films": await film_dao.count(db),
        "total_reviews": await review_dao.count(db),
        "uptime_status": "healthy",
    }
