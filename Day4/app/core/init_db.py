"""
Database table initialization utility for local development, experimentation, and testing.

Usage:
    python -m app.core.init_db

Production Note:
- Base.metadata.create_all() creates missing tables only.
- It does not manage schema evolution.
- Production applications should use Alembic migrations instead.
"""
from __future__ import annotations

import asyncio
import logging

from app.core.database import Base, engine, init_db
# Import ORM models to ensure they are registered in Base.metadata
from app.schemas import Film, Review, User  # noqa: F401

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("film_review.init_db")


async def main() -> None:
    logger.info("Initializing database tables...")
    await init_db(engine)
    await engine.dispose()
    logger.info("Database tables created successfully.")


if __name__ == "__main__":
    asyncio.run(main())
