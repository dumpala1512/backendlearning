from __future__ import annotations

import os
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

import app.models  # Ensures all ORM models are registered in metadata
from app.core.database import Base

# Isolated test database URL: default to in-memory SQLite with aiosqlite and StaticPool
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "sqlite+aiosqlite:///:memory:")


def create_test_engine(database_url: str | None = None) -> AsyncEngine:
    """
    Create an isolated async SQLAlchemy engine for integration testing.
    Never connects to the production database.
    """
    url = database_url or TEST_DATABASE_URL
    is_sqlite = "sqlite" in url

    connect_args = {"check_same_thread": False} if is_sqlite else {}
    poolclass = StaticPool if is_sqlite else None

    engine_kwargs: dict[str, Any] = {
        "echo": False,
        "connect_args": connect_args,
    }
    if poolclass is not None:
        engine_kwargs["poolclass"] = poolclass

    return create_async_engine(url, **engine_kwargs)


async def init_test_db(engine: AsyncEngine) -> None:
    """
    Create the database schema once for the test session.
    Avoids dropping and recreating tables before every test.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_test_db(engine: AsyncEngine) -> None:
    """Drop the database schema upon test session completion."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


def get_test_session_factory(
    engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    """Provide a sessionmaker factory configured for the test engine."""
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
