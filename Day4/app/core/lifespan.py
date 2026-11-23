from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.core.config import settings
from app.core.redis import close_redis, init_redis
from app.events.publisher import create_event_publisher
from app.logging import configure_logging
from app.storage.storage_service import StorageService

# Configure structured JSON logging globally
configure_logging()
logger = logging.getLogger("film_review_platform")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for application startup and shutdown events.
    Replaces deprecated @app.on_event.
    """
    # Startup logic: database, logging, shared Redis connection, S3 storage
    logger.info("Starting up Film Review Platform API...")
    await init_redis()

    app.state.event_publisher = create_event_publisher(settings)

    storage_service = StorageService(settings=settings)
    app.state.storage_service = storage_service
    try:
        await storage_service.verify_bucket_access()
    except Exception:
        logger.exception("Storage startup validation failed. Application startup aborted.")
        raise

    yield

    # Shutdown logic: gracefully close Redis and storage connections
    logger.info("Shutting down Film Review Platform API...")
    await close_redis()
    await storage_service.close()

