from __future__ import annotations


from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings
from app.core.project_config import DEBUG



class Base(DeclarativeBase):
    """
    SQLAlchemy 2.0 Base class using typed DeclarativeBase.
    All ORM models inherit from this base.
    """
    pass


# Production-ready async engine using connection string from centralized settings
engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,                                 # disabled SQL logging to avoid polluting stdout
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,                         # checks if the connection is alive before using it
    pool_recycle=1800,                          # recycle connections after 1800seconds ie 30mins to avoid stale connections
)

# Async sessionmaker factory: creates request-scoped AsyncSession instances
async_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,                    # prevents detaching session objects from database after commit 
    autoflush=False,                           # prevents auto-flushing of session which can lead to unexpected queries
)

