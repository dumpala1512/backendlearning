from __future__ import annotations

import uuid
from typing import AsyncGenerator

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, settings
from app.core.database import async_session_factory

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
    x_trace_id: str | None = Header(default=None, alias="X-Trace-Id"),
) -> str:
    """Retrieve client X-Trace-Id header or generate a new UUID4."""
    if x_trace_id and x_trace_id.strip():
        return x_trace_id.strip()
    return str(uuid.uuid4())
