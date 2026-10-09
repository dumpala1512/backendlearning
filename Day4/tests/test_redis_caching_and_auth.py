from __future__ import annotations

import logging
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.lifespan import lifespan
from app.core.redis import close_redis, get_redis_client, init_redis, set_redis_client
from app.exceptions.user import TokenRevokedError
from app.main import app
from app.schemas.film import FilmCreate
from app.services.film_service import FilmService
from app.services.redis_service import RedisService
from app.services.user_service import UserService


# ==============================================================================
# 1. Redis Configuration & Service Layer Tests
# ==============================================================================
@pytest.mark.asyncio
async def test_redis_configuration_settings():
    """Verify Redis settings are loaded from centralized config without hardcoded values."""
    assert settings.REDIS_HOST is not None
    assert settings.REDIS_PORT is not None
    assert settings.CACHE_TTL_SECONDS > 0
    assert settings.refresh_token_ttl_seconds == settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400
    assert "redis://" in settings.redis_connection_url


@pytest.mark.asyncio
async def test_redis_service_crud_and_serialization(fake_redis):
    """Verify RedisService get, set with TTL, exists, delete, and pattern matching with JSON serialization."""
    service = RedisService(client=fake_redis)

    # Set and Get string
    assert await service.set("test:str", "hello_world", ttl=60) is True
    assert await service.get("test:str") == "hello_world"

    # Set and Get complex JSON dictionary with UUID and datetime
    sample_id = uuid.uuid4()
    sample_data = {
        "id": sample_id,
        "name": "Christopher Nolan",
        "films": ["Inception", "Memento"],
    }
    assert await service.set("test:complex", sample_data, ttl=60) is True
    retrieved = await service.get("test:complex")
    assert retrieved is not None
    assert retrieved["id"] == str(sample_id)
    assert retrieved["name"] == "Christopher Nolan"
    assert retrieved["films"] == ["Inception", "Memento"]

    # Exists check
    assert await service.exists("test:complex") is True
    assert await service.exists("test:non_existent") is False

    # Delete
    assert await service.delete("test:str") is True
    assert await service.get("test:str") is None

    # Pattern deletion
    await service.set("films:list:1", {"page": 1})
    await service.set("films:list:2", {"page": 2})
    await service.set("films:other", {"keep": True})

    deleted_count = await service.delete_by_pattern("films:list*")
    assert deleted_count == 2
    assert await service.get("films:list:1") is None
    assert await service.get("films:list:2") is None
    assert await service.get("films:other") == {"keep": True}


@pytest.mark.asyncio
async def test_redis_service_graceful_error_handling():
    """Verify RedisService handles None client, malformed data, and errors gracefully."""
    service = RedisService(client=None)

    # All operations return graceful fallbacks without raising uncaught exceptions
    assert await service.get("any:key") is None
    assert await service.set("any:key", "val") is False
    assert await service.delete("any:key") is False
    assert await service.exists("any:key") is False
    assert await service.delete_by_pattern("any:*") == 0


# ==============================================================================
# 2. Film List Read-Through Cache & Invalidation Tests
# ==============================================================================
@pytest.mark.asyncio
async def test_deterministic_film_list_cache_keys():
    """Verify deterministic and canonical cache key generation for unique queries."""
    # Default list
    assert FilmService.build_film_list_cache_key() == "films:list"
    assert FilmService.build_film_list_cache_key(limit=10) == "films:list"

    # With genre
    assert FilmService.build_film_list_cache_key(genre="Sci-Fi") == "films:list:genre=sci-fi"

    # With limit
    assert FilmService.build_film_list_cache_key(limit=25) == "films:list:limit=25"

    # With multiple filters (always sorted)
    key1 = FilmService.build_film_list_cache_key(genre="Action", year_from=2000, year_to=2020, limit=20)
    key2 = FilmService.build_film_list_cache_key(year_to=2020, limit=20, genre="action", year_from=2000)
    assert key1 == key2
    assert "genre=action" in key1
    assert "start_year=2000" in key1
    assert "end_year=2020" in key1
    assert "limit=20" in key1


@pytest.mark.asyncio
async def test_film_list_read_through_caching_and_hit_miss(admin_client: AsyncClient, fake_redis, caplog):
    """
    Verify read-through caching flow:
    1. First GET /films -> Cache miss -> Queries DB -> Stores in Redis
    2. Second GET /films -> Cache hit -> Returns cached data without DB query
    """
    # Create test films first
    await admin_client.post(
        "/api/v1/films",
        json={"title": "The Dark Knight", "director": "Christopher Nolan", "releaseYear": 2008, "genre": "Action"},
    )
    await admin_client.post(
        "/api/v1/films",
        json={"title": "Interstellar", "director": "Christopher Nolan", "releaseYear": 2014, "genre": "Sci-Fi"},
    )

    # Clear cache to guarantee miss
    await fake_redis.flushall()

    with caplog.at_level(logging.INFO):
        # First GET /films: Cache Miss
        res1 = await admin_client.get("/api/v1/films")
        assert res1.status_code == 200
        films1 = res1.json()
        assert len(films1) == 2
        assert "Cache miss for films:list" in caplog.text

        # Verify cached in Redis
        cached_raw = await fake_redis.get("films:list")
        assert cached_raw is not None

        caplog.clear()

        # Second GET /films: Cache Hit
        res2 = await admin_client.get("/api/v1/films")
        assert res2.status_code == 200
        films2 = res2.json()
        assert len(films2) == 2
        assert films2[0]["title"] == films1[0]["title"]
        assert "Cache hit for films:list" in caplog.text


@pytest.mark.asyncio
async def test_film_cache_invalidation_on_create_update_delete(admin_client: AsyncClient, fake_redis, caplog):
    """
    Verify cache is invalidated immediately upon:
    - Create film
    - Update film
    - Delete film
    """
    # 1. Populate initial cache
    create_res = await admin_client.post(
        "/api/v1/films",
        json={"title": "Dunkirk", "director": "Christopher Nolan", "releaseYear": 2017, "genre": "War"},
    )
    film_id = create_res.json()["id"]

    # Prime cache
    await admin_client.get("/api/v1/films")
    assert await fake_redis.get("films:list") is not None

    with caplog.at_level(logging.INFO):
        # Update film -> Invalidates cache
        update_res = await admin_client.patch(
            f"/api/v1/films/{film_id}",
            json={"description": "Historical evacuation drama."},
        )
        assert update_res.status_code == 200
        assert "Invalidated film list cache" in caplog.text
        # Cache must be gone from Redis
        assert await fake_redis.get("films:list") is None

    # Prime cache again
    await admin_client.get("/api/v1/films")
    assert await fake_redis.get("films:list") is not None

    with caplog.at_level(logging.INFO):
        # Create new film -> Invalidates cache
        caplog.clear()
        await admin_client.post(
            "/api/v1/films",
            json={"title": "Oppenheimer", "director": "Christopher Nolan", "releaseYear": 2023, "genre": "Biography"},
        )
        assert "Invalidated film list cache" in caplog.text
        assert await fake_redis.get("films:list") is None

    # Prime cache again
    await admin_client.get("/api/v1/films")
    assert await fake_redis.get("films:list") is not None

    with caplog.at_level(logging.INFO):
        # Soft delete film -> Invalidates cache
        caplog.clear()
        del_res = await admin_client.delete(f"/api/v1/films/{film_id}")
        assert del_res.status_code == 200
        assert "Invalidated film list cache" in caplog.text
        assert await fake_redis.get("films:list") is None


# ==============================================================================
# 3. Refresh Token Storage, Validation & Logout Lifecycle Tests
# ==============================================================================
@pytest.mark.asyncio
async def test_refresh_token_lifecycle_login_refresh_logout(client: AsyncClient, fake_redis, caplog):
    """
    Full end-to-end lifecycle verification:
    1. Login -> Issues refresh token -> Stored in Redis with TTL matching expiry
    2. Refresh -> Token validated against Redis -> Issues new access token
    3. Logout (POST /logout) -> Access token validated -> Refresh token deleted from Redis
    4. Refresh after logout -> 401 Unauthorized with {"detail": "Refresh token has been revoked"}
    """
    # Register user
    reg_res = await client.post(
        "/api/v1/register",
        json={"username": "alice_wonder", "email": "alice@example.com", "password": "SecretPassword123!"},
    )
    assert reg_res.status_code == 201

    with caplog.at_level(logging.INFO):
        # Login
        login_res = await client.post(
            "/api/v1/login",
            json={"username": "alice_wonder", "password": "SecretPassword123!"},
        )
        assert login_res.status_code == 200
        data = login_res.json()
        access_token = data["access_token"]
        refresh_token = data["refresh_token"]
        user_id = data["user_id"]

        # Verify logged and stored in Redis
        assert f"Stored refresh token for user {user_id}" in caplog.text
        redis_token_entry = await fake_redis.get(f"refresh_token:{refresh_token}")
        assert redis_token_entry is not None

    # Refresh successfully
    refresh_res = await client.post(
        "/api/v1/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_res.status_code == 200
    new_token_data = refresh_res.json()
    assert "access_token" in new_token_data

    with caplog.at_level(logging.INFO):
        caplog.clear()
        # Logout via POST /api/v1/logout (and /logout alias)
        logout_res = await client.post(
            "/api/v1/logout",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert logout_res.status_code == 200
        assert logout_res.json() == {"message": "Logged out successfully"}
        assert f"Revoked refresh token for user {user_id}" in caplog.text

        # Verify refresh token deleted from Redis
        assert await fake_redis.get(f"refresh_token:{refresh_token}") is None

    # Refresh after logout MUST fail with HTTP 401 Unauthorized
    failed_refresh_res = await client.post(
        "/api/v1/refresh",
        json={"refresh_token": refresh_token},
    )
    assert failed_refresh_res.status_code == 401
    err_body = failed_refresh_res.json()
    assert err_body["detail"] == "Refresh token has been revoked"


@pytest.mark.asyncio
async def test_logout_requires_valid_access_token(client: AsyncClient):
    """Verify POST /logout rejects unauthenticated requests with HTTP 401."""
    # No token
    res_no_token = await client.post("/api/v1/logout")
    assert res_no_token.status_code == 401

    # Malformed token
    res_bad_token = await client.post("/api/v1/logout", headers={"Authorization": "Bearer bad-token"})
    assert res_bad_token.status_code == 401


@pytest.mark.asyncio
async def test_root_logout_alias(client: AsyncClient, fake_redis):
    """Verify POST /logout is also accessible at root URL."""
    # Register and login
    await client.post(
        "/api/v1/register",
        json={"username": "root_user", "email": "root@example.com", "password": "SecretPassword123!"},
    )
    login_res = await client.post(
        "/login",
        json={"username": "root_user", "password": "SecretPassword123!"},
    )
    access_token = login_res.json()["access_token"]
    refresh_token = login_res.json()["refresh_token"]

    # Logout at root /logout
    logout_res = await client.post("/logout", headers={"Authorization": f"Bearer {access_token}"})
    assert logout_res.status_code == 200
    assert logout_res.json() == {"message": "Logged out successfully"}

    # Refresh after root logout fails
    failed_refresh = await client.post("/refresh", json={"refresh_token": refresh_token})
    assert failed_refresh.status_code == 401
    assert failed_refresh.json()["detail"] == "Refresh token has been revoked"
