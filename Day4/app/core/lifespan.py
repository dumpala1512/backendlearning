from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

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
    # Startup logic
    logger.info("Starting up Film Review Platform API...")

    yield

    # Shutdown logic
    logger.info("Shutting down Film Review Platform API...")
