from __future__ import annotations

import uuid
from typing import Generator

from fastapi import Depends, Header

from app.core.config import Settings, settings


def get_settings() -> Settings:
    """Provide the application Settings singleton."""
    return settings


class DatabaseSession:
    """Placeholder database session for Day 3.Mock/simulation of a real database"""

    def __init__(self, connection_url: str, session_id: str | None = None) -> None:
        self.session_id: str = session_id or str(uuid.uuid4())
        self.connection_url: str = connection_url
        self.is_active: bool = True

    def execute(self, query: str) -> dict[str, str]:
        if not self.is_active:
            raise RuntimeError(f"Cannot execute query on closed DatabaseSession {self.session_id}")
        return {"session_id": self.session_id, "query": query, "status": "executed"}

    def close(self) -> None:
        self.is_active = False


def get_db(
    app_settings: Settings = Depends(get_settings),
) -> Generator[DatabaseSession, None, None]:                        #Generator[YieldType, SendType, ReturnType]
    """Provide a database session and ensure cleanup after request completion."""
    session = DatabaseSession(connection_url=app_settings.DATABASE_URL)
    try:
        yield session
    finally:
        session.close()


def get_trace_id(
    x_trace_id: str | None = Header(default=None, alias="X-Trace-Id"),
) -> str:
    """Retrieve client X-Trace-Id header or generate a new UUID4."""
    if x_trace_id and x_trace_id.strip():
        return x_trace_id.strip()
    return str(uuid.uuid4())
