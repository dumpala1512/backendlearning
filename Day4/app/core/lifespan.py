import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

# Configure logger
logger = logging.getLogger("film_review_platform")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for application startup and shutdown events.
    Replaces deprecated @app.on_event.
    """
    # Startup logic
    logger.info("Starting up Film Review Platform API...")
    # (Initialize connection pools, caches, etc. here if needed)

    yield

    # Shutdown logic
    logger.info("Shutting down Film Review Platform API...")
    # (Clean up connection pools, close files, etc. here)
