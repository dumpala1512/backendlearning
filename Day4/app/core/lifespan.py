from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.core.redis import close_redis, init_redis
from app.logging import configure_logging

# Configure structured JSON logging globally
configure_logging()
logger = logging.getLogger("film_review_platform")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for application startup and shutdown events.
    Replaces deprecated @app.on_event.
    """
    # Startup logic: database, logging, shared Redis connection
    logger.info("Starting up Film Review Platform API...")
    await init_redis()

    yield

    # Shutdown logic: gracefully close Redis and connections
    logger.info("Shutting down Film Review Platform API...")
    await close_redis()

