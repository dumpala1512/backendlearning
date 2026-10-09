from __future__ import annotations

import json
import logging
from datetime import date, datetime
from typing import Any
import uuid

from fastapi import Depends
from pydantic import BaseModel
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.redis import get_redis_client

logger = logging.getLogger("film_review.services.redis")


class CustomJSONEncoder(json.JSONEncoder):
    """Encodes UUIDs, datetimes, Pydantic models, and sets into valid JSON primitives."""

    def default(self, o: Any) -> Any:
        if isinstance(o, (datetime, date)):
            return o.isoformat()
        if isinstance(o, uuid.UUID):
            return str(o)
        if isinstance(o, BaseModel):
            return o.model_dump(mode="json")
        if isinstance(o, set):
            return list(o)
        if hasattr(o, "__dict__"):
            # SQLAlchemy ORM instances or dataclasses
            d = dict(o.__dict__)
            d.pop("_sa_instance_state", None)
            return d
        return super().default(o)


class RedisService:
    """
    Reusable Redis service abstracting low-level Redis operations and JSON serialization.
    Ensures complete layer separation: no routes interact with Redis directly.
    Provides graceful error handling for connection timeouts, serialization errors, and Redis downtime.
    """

    def __init__(self, client: Redis | None = Depends(get_redis_client)) -> None:
        self._injected_client = client

    @property
    def client(self) -> Redis | None:
        return self._injected_client if self._injected_client is not None else get_redis_client()

    def _serialize(self, value: Any) -> str:
        """Serialize Python objects/models to JSON string."""
        return json.dumps(value, cls=CustomJSONEncoder)

    def _deserialize(self, raw_value: str | bytes | None) -> Any | None:
        """Deserialize JSON string back into Python objects."""
        if raw_value is None:
            return None
        if isinstance(raw_value, bytes):
            raw_value = raw_value.decode("utf-8")
        return json.loads(raw_value)

    async def get(self, key: str) -> Any | None:
        """
        Retrieve and JSON-deserialize a value by key.
        Returns None on cache miss, Redis error, or deserialization failure.
        """
        cli = self.client
        if cli is None:
            return None
        try:
            raw = await cli.get(key)
            if raw is None:
                return None
            return self._deserialize(raw)
        except (RedisError, OSError) as exc:
            logger.error("Redis get failed for key '%s': %s", key, exc)
            return None
        except json.JSONDecodeError as exc:
            logger.error("JSON decode failed for key '%s': %s", key, exc)
            return None
        except Exception as exc:
            logger.error("Unexpected failure getting key '%s' from Redis: %s", key, exc)
            return None

    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """
        JSON-serialize and store a value in Redis with optional TTL in seconds.
        Returns True on success, False on failure.
        """
        cli = self.client
        if cli is None:
            return False
        try:
            payload = self._serialize(value)
        except Exception as exc:
            logger.error("Serialization failed for key '%s': %s", key, exc)
            return False

        try:
            if ttl is not None and ttl > 0:
                await cli.set(key, payload, ex=ttl)
            else:
                await cli.set(key, payload)
            return True
        except (RedisError, OSError) as exc:
            logger.error("Redis set failed for key '%s': %s", key, exc)
            return False
        except Exception as exc:
            logger.error("Unexpected failure setting key '%s' in Redis: %s", key, exc)
            return False

    async def delete(self, key: str) -> bool:
        """
        Delete a specific key from Redis.
        Returns True if deleted, False otherwise.
        """
        cli = self.client
        if cli is None:
            return False
        try:
            deleted_count = await cli.delete(key)
            return deleted_count > 0
        except (RedisError, OSError) as exc:
            logger.error("Redis delete failed for key '%s': %s", key, exc)
            return False
        except Exception as exc:
            logger.error("Unexpected failure deleting key '%s' from Redis: %s", key, exc)
            return False

    async def exists(self, key: str) -> bool:
        """
        Check if a key exists in Redis.
        """
        cli = self.client
        if cli is None:
            return False
        try:
            count = await cli.exists(key)
            return count > 0
        except (RedisError, OSError) as exc:
            logger.error("Redis exists check failed for key '%s': %s", key, exc)
            return False
        except Exception as exc:
            logger.error("Unexpected failure checking existence of key '%s': %s", key, exc)
            return False

    async def delete_by_pattern(self, pattern: str) -> int:
        """
        Find and delete all keys matching the glob pattern (e.g., 'films:list*').
        Uses scan_iter to avoid blocking Redis on large keyspaces.
        Returns count of deleted keys.
        """
        cli = self.client
        if cli is None:
            return 0
        try:
            keys: list[str] = []
            async for k in cli.scan_iter(match=pattern):
                keys.append(k)
            if keys:
                deleted_count = await cli.delete(*keys)
                return deleted_count
            return 0
        except (RedisError, OSError) as exc:
            logger.error("Redis delete_by_pattern failed for '%s': %s", pattern, exc)
            return 0
        except Exception as exc:
            logger.error("Unexpected failure in delete_by_pattern for '%s': %s", pattern, exc)
            return 0
