from __future__ import annotations

import logging
from typing import Any
import redis.asyncio as aioredis
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.config import settings

logger = logging.getLogger("film_review.redis")

# Shared Redis client singleton managed by FastAPI lifespan
_redis_client: Redis | None = None


async def init_redis() -> Redis | None:
    """
    Initialize a shared async Redis connection pool and client.
    Called once during FastAPI application startup via lifespan.
    Reads connection details exclusively from settings.
    """
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    connection_url = settings.redis_connection_url
    logger.info("Initializing Redis connection to %s...", settings.REDIS_HOST)

    try:
        _redis_client = aioredis.from_url(
            connection_url,
            decode_responses=True,                        
            socket_timeout=5.0,                           #if command fails to recieve a response it will raise timeout error
            socket_connect_timeout=5.0,                   #if connection to server fails it will raise timeout error
            health_check_interval=30,
        )
        # Verify connectivity
        await _redis_client.ping()
        logger.info("Successfully connected to Redis at %s:%s (db=%s)", settings.REDIS_HOST, settings.REDIS_PORT, settings.REDIS_DB)
    except (RedisError, OSError) as exc:
        logger.warning(
            "Redis is currently unavailable at %s:%s (%s). API will operate with cache disabled/degraded.",
            settings.REDIS_HOST,
            settings.REDIS_PORT,
            exc,
        )

    return _redis_client


async def close_redis() -> None:
    """
    Close the shared Redis connection.
    Called once during FastAPI application shutdown via lifespan.
    """
    global _redis_client
    if _redis_client is not None:
        logger.info("Closing Redis connection...")
        try:
            await _redis_client.aclose()
        except Exception as exc:
            logger.error("Error closing Redis connection: %s", exc)
        finally:
            _redis_client = None
        logger.info("Redis connection closed.")


def get_redis_client() -> Redis | None:
    """
    Dependency provider returning the shared Redis client singleton.
    Does NOT open a new connection per request.
    """
    return _redis_client


def set_redis_client(client: Redis | None) -> None:
    """Explicitly assign the Redis client singleton (useful in test harnesses)."""
    global _redis_client
    _redis_client = client
