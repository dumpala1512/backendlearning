from __future__ import annotations

from typing import Sequence

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas import UserORM


async def get_by_id(db: AsyncSession, user_id: int) -> UserORM | None:
    """Find a user by primary key ID asynchronously via SQLAlchemy."""
    query = select(UserORM).where(UserORM.id == user_id)
    result = await db.execute(query)
    return result.scalars().first()


async def get_by_username(db: AsyncSession, username: str) -> UserORM | None:
    """Find a user by username asynchronously via SQLAlchemy."""
    raw = username.strip()
    norm = raw.lower()
    norm_underscore = norm.replace(" ", "_")
    norm_space = norm.replace("_", " ")
    query = select(UserORM).where(
        or_(
            UserORM.username == raw,
            func.lower(UserORM.username) == norm,
            func.lower(UserORM.username) == norm_underscore,
            func.lower(UserORM.username) == norm_space,
        )
    )
    result = await db.execute(query)
    return result.scalars().first()


async def get_by_email(db: AsyncSession, email: str) -> UserORM | None:
    """Find a user by email asynchronously via SQLAlchemy."""
    query = select(UserORM).where(UserORM.email == email.strip().lower())
    result = await db.execute(query)
    return result.scalars().first()


async def create(
    db: AsyncSession,
    username: str,
    email: str,
    hashed_password: str,
    role: str = "user",
) -> UserORM:
    """Insert a new user into PostgreSQL asynchronously."""
    new_user = UserORM(
        username=username.strip(),
        email=email.strip().lower(),
        hashed_password=hashed_password,
        role=role.strip().lower(),
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


async def get_all(db: AsyncSession, limit: int = 50) -> Sequence[UserORM]:
    """List users asynchronously via SQLAlchemy."""
    query = select(UserORM).order_by(UserORM.id.asc()).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


async def count(db: AsyncSession) -> int:
    """Count users asynchronously via SQLAlchemy."""
    query = select(func.count(UserORM.id))
    result = await db.execute(query)
    return result.scalar_one() or 0


# Backwards compatibility aliases
get_by_id_async = get_by_id
get_by_username_async = get_by_username
get_by_email_async = get_by_email
create_async = create
list_all_async = get_all
count_async = count
