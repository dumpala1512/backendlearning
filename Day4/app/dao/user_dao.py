from __future__ import annotations

from typing import Sequence
import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserORM


class UserDAO:
    """
    Data Access Object for User entities.
    Encapsulates all asynchronous SQLAlchemy 2.0 database queries for users.
    Uses UUID for user_id.
    """

    async def get_by_email(
        self,
        session: AsyncSession,
        email: str,
    ) -> User | None:
        """
        Find a user by email using select() and scalar_one_or_none().
        Returns User or None if not found.
        """
        query = select(User).where(User.email == email.strip().lower())
        result = await session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_id(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
    ) -> User | None:
        """Find a user by UUID primary key asynchronously."""
        query = select(User).where(User.id == user_id)
        result = await session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_username(
        self,
        session: AsyncSession,
        username: str,
    ) -> User | None:
        """Find a user by username asynchronously."""
        raw = username.strip()
        norm = raw.lower()
        norm_underscore = norm.replace(" ", "_")
        norm_space = norm.replace("_", " ")
        query = select(User).where(
            or_(
                User.username == raw,
                func.lower(User.username) == norm,
                func.lower(User.username) == norm_underscore,
                func.lower(User.username) == norm_space,
            )
        )
        result = await session.execute(query)
        return result.scalar_one_or_none()

    async def create(
        self,
        session: AsyncSession,
        username: str,
        email: str,
        hashed_password: str,
        role: str = "user",
        full_name: str = "",
    ) -> User:
        """Insert and persist a new user into PostgreSQL with UUID PK and full_name."""
        new_user = User(
            username=username.strip(),
            full_name=full_name.strip(),
            email=email.strip().lower(),
            hashed_password=hashed_password,
            role=role.strip().lower(),
        )
        session.add(new_user)
        await session.commit()
        await session.refresh(new_user)
        return new_user

    async def get_all(
        self,
        session: AsyncSession,
        limit: int = 50,
    ) -> list[User]:
        """List users asynchronously via select() and scalars().all()."""
        query = select(User).order_by(User.created_at.desc(), User.id.asc()).limit(limit)
        result = await session.execute(query)
        return list(result.scalars().all())

    async def count(self, session: AsyncSession) -> int:
        """Count users asynchronously via func.count."""
        query = select(func.count(User.id))
        result = await session.execute(query)
        return result.scalar_one() or 0


# Default singleton and module-level functions for backward compatibility
default_user_dao = UserDAO()


async def get_by_email(db: AsyncSession, email: str) -> User | None:
    return await default_user_dao.get_by_email(session=db, email=email)


async def get_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    return await default_user_dao.get_by_id(session=db, user_id=user_id)


async def get_by_username(db: AsyncSession, username: str) -> User | None:
    return await default_user_dao.get_by_username(session=db, username=username)


async def create(
    db: AsyncSession,
    username: str,
    email: str,
    hashed_password: str,
    role: str = "user",
    full_name: str = "",
) -> User:
    return await default_user_dao.create(
        session=db,
        username=username,
        email=email,
        hashed_password=hashed_password,
        role=role,
        full_name=full_name,
    )


async def get_all(db: AsyncSession, limit: int = 50) -> Sequence[User]:
    return await default_user_dao.get_all(session=db, limit=limit)


async def count(db: AsyncSession) -> int:
    return await default_user_dao.count(session=db)


get_by_id_async = get_by_id
get_by_username_async = get_by_username
get_by_email_async = get_by_email
create_async = create
list_all_async = get_all
count_async = count
