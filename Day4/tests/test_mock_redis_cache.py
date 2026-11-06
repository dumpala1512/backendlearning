from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import uuid
from unittest.mock import AsyncMock, MagicMock, call, patch
import pytest
from pytest_mock import MockerFixture
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.dao.film_dao import FilmDAO
from app.models.film import Film
from app.schemas.film import FilmResponse
from app.services.film_service import FilmService
from app.services.redis_service import RedisService

# Mark all tests in this file with the 'redis' marker
pytestmark = [pytest.mark.redis]


@pytest.fixture
def sample_film() -> Film:
    """Fixture providing a mockable Film ORM entity."""
    return Film(
        id=uuid.UUID("11111111-2222-3333-4444-555555555555"),
        title="Interstellar",
        director="Christopher Nolan",
        release_year=2014,
        genre="Sci-Fi",
        description="A team of explorers travel through a wormhole in space in an attempt to ensure humanity's survival.",
        is_active=True,
        created_at=datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        total_reviews=5,
        average_rating=9.2,
    )


@pytest.fixture
def serialized_film(sample_film: Film) -> dict[str, Any]:
    """Serialized representation of sample_film matching FilmService._serialize_film."""
    return FilmService._serialize_film(sample_film)


# ===========================================================================
# 1. Cache Miss Tests
# ===========================================================================


@pytest.mark.unit
async def test_film_cache_miss_flow_using_mocker(
    mocker: MockerFixture,
    sample_film: Film,
    serialized_film: dict[str, Any],
) -> None:
    """
    Requirement 1 & 5: Cache Miss Test using pytest-mock `mocker`.

    Simulates the exact flow:
    1. Redis does not contain the film (get returns None)
    2. The service queries the database (dao.get_by_id)
    3. The database returns a film
    4. The service serializes the result
    5. The result is stored in Redis (set called with cache_key, serialized payload, and TTL)
    6. The returned object matches the database result

    Assertions verify:
    - Redis get() called exactly once
    - Database DAO get_by_id() called exactly once
    - Redis set() called exactly once
    - Cache key is exactly correct
    - Cached value matches serialized film
    """
    film_id = sample_film.id
    expected_cache_key = FilmService.build_film_cache_key(film_id)
    assert expected_cache_key == f"film:{film_id}"

    # AsyncMock for async dependencies: RedisService and FilmDAO
    mock_redis = mocker.MagicMock(spec=RedisService)
    mock_redis.get = mocker.AsyncMock(return_value=None)
    mock_redis.set = mocker.AsyncMock(return_value=True)

    mock_dao = mocker.MagicMock(spec=FilmDAO)
    mock_dao.get_by_id = mocker.AsyncMock(return_value=sample_film)

    # Mock database session
    mock_session = mocker.MagicMock(spec=AsyncSession)

    # Instantiate service under test
    service = FilmService(dao=mock_dao, redis_service=mock_redis)

    # Act
    result = await service.get_by_id(session=mock_session, film_id=film_id)

    # Assert 1: Redis get() called exactly once with exact cache key
    mock_redis.get.assert_called_once_with(expected_cache_key)
    assert mock_redis.get.call_count == 1

    # Assert 2: Database DAO method called exactly once
    mock_dao.get_by_id.assert_called_once_with(mock_session, film_id)
    assert mock_dao.get_by_id.call_count == 1

    # Assert 3 & 4 & 5: Redis set() called exactly once with key, serialized film, and TTL
    mock_redis.set.assert_called_once()
    assert mock_redis.set.call_count == 1

    # Inspect call args for precise parameter matching
    args, kwargs = mock_redis.set.call_args
    assert args[0] == expected_cache_key
    assert args[1] == serialized_film
    assert kwargs.get("ttl") == settings.CACHE_TTL_SECONDS

    # Assert 6: Returned object matches the database result
    assert result == sample_film
    assert result.id == sample_film.id
    assert result.title == sample_film.title


@pytest.mark.unit
async def test_film_cache_miss_using_unittest_patch_decorator(
    sample_film: Film,
    serialized_film: dict[str, Any],
) -> None:
    """
    Requirement 5: Demonstrate unittest.mock.patch as a decorator.
    Shows how patch temporarily replaces the target object during the test
    and automatically restores the original object afterward.
    """
    film_id = sample_film.id
    expected_key = f"film:{film_id}"

    mock_redis = MagicMock(spec=RedisService)
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.set = AsyncMock(return_value=True)

    with patch.object(FilmDAO, "get_by_id", new_callable=AsyncMock) as mock_dao_get:
        mock_dao_get.return_value = sample_film
        mock_session = MagicMock(spec=AsyncSession)

        service = FilmService(dao=FilmDAO(), redis_service=mock_redis)
        result = await service.get_by_id(session=mock_session, film_id=film_id)

        # Assertions
        mock_redis.get.assert_called_once_with(expected_key)
        mock_dao_get.assert_called_once_with(mock_session, film_id)
        mock_redis.set.assert_called_once_with(
            expected_key,
            serialized_film,
            ttl=settings.CACHE_TTL_SECONDS,
        )
        assert result.title == sample_film.title

    # Verify original FilmDAO.get_by_id is restored after context manager exits
    assert not isinstance(FilmDAO.get_by_id, AsyncMock)


# ===========================================================================
# 2. Cache Hit Tests
# ===========================================================================


@pytest.mark.unit
async def test_film_cache_hit_flow_using_mocker(
    mocker: MockerFixture,
    sample_film: Film,
    serialized_film: dict[str, Any],
) -> None:
    """
    Requirement 1 & 5: Cache Hit Test using pytest-mock `mocker`.

    Simulates:
    1. Redis already contains the film
    2. Service returns cached data directly

    Assertions verify:
    - Redis get() called once
    - DAO/database NEVER called (assert_not_called)
    - Redis set() NEVER called (assert_not_called)
    - Returned object matches cached object deserialized
    """
    film_id = sample_film.id
    expected_cache_key = f"film:{film_id}"

    # Arrange: Redis get returns cached serialized dictionary
    mock_redis = mocker.MagicMock(spec=RedisService)
    mock_redis.get = mocker.AsyncMock(return_value=serialized_film)
    mock_redis.set = mocker.AsyncMock()

    mock_dao = mocker.MagicMock(spec=FilmDAO)
    mock_dao.get_by_id = mocker.AsyncMock()

    mock_session = mocker.MagicMock(spec=AsyncSession)
    service = FilmService(dao=mock_dao, redis_service=mock_redis)

    # Act
    result = await service.get_by_id(session=mock_session, film_id=film_id)

    # Assert 1: Redis get called once with the exact key
    mock_redis.get.assert_called_once_with(expected_cache_key)
    assert mock_redis.get.call_count == 1

    # Assert 2: Database DAO is NEVER called on cache hit
    mock_dao.get_by_id.assert_not_called()
    assert mock_dao.get_by_id.call_count == 0

    # Assert 3: Redis set is NEVER called on cache hit
    mock_redis.set.assert_not_called()
    assert mock_redis.set.call_count == 0

    # Assert 4: Returned object equals cached object
    assert isinstance(result, FilmResponse)
    assert result.id == sample_film.id
    assert result.title == sample_film.title
    assert result.release_year == sample_film.release_year


@pytest.mark.unit
@patch.object(RedisService, "get", new_callable=AsyncMock)
@patch.object(RedisService, "set", new_callable=AsyncMock)
@patch.object(FilmDAO, "get_by_id", new_callable=AsyncMock)
async def test_film_cache_hit_using_patch_decorators(
    mock_dao_get: AsyncMock,
    mock_redis_set: AsyncMock,
    mock_redis_get: AsyncMock,
    sample_film: Film,
    serialized_film: dict[str, Any],
) -> None:
    """
    Requirement 5: Demonstrate unittest.mock.patch decorator stacking.
    Validates automatic teardown and assertion methods.
    """
    film_id = sample_film.id
    mock_redis_get.return_value = serialized_film
    mock_session = MagicMock(spec=AsyncSession)

    redis_service = RedisService(client=None)
    service = FilmService(dao=FilmDAO(), redis_service=redis_service)

    result = await service.get_by_id(session=mock_session, film_id=film_id)

    # Assertions using mock assertion API
    mock_redis_get.assert_called_once()
    mock_dao_get.assert_not_called()
    mock_redis_set.assert_not_called()
    assert result.id == sample_film.id


# ===========================================================================
# 3. Low-Level Redis Client Mock Tests (Direct get, set, delete)
# ===========================================================================


@pytest.mark.unit
async def test_redis_service_low_level_client_mock(mocker: MockerFixture) -> None:
    """
    Test RedisService wrapper interacting directly with a mocked low-level redis.asyncio.Redis client.
    Demonstrates:
    - assert_called()
    - assert_called_once()
    - assert_called_once_with(...)
    - assert_has_calls(...)
    - call_args_list
    """
    # Create low-level mock Redis client
    mock_client = mocker.AsyncMock()
    mock_client.get = mocker.AsyncMock(return_value='{"title": "Memento", "year": 2000}')
    mock_client.set = mocker.AsyncMock(return_value=True)
    mock_client.delete = mocker.AsyncMock(return_value=1)

    redis_service = RedisService(client=mock_client)

    # Test GET
    val = await redis_service.get("films:test_key")
    assert val == {"title": "Memento", "year": 2000}
    mock_client.get.assert_called_once_with("films:test_key")

    # Test SET with TTL
    success = await redis_service.set("films:test_key", {"title": "Memento"}, ttl=300)
    assert success is True
    mock_client.set.assert_called_once()
    # Check set was called with ex=300
    _, kwargs = mock_client.set.call_args
    assert kwargs.get("ex") == 300

    # Test DELETE
    del_ok = await redis_service.delete("films:test_key")
    assert del_ok is True
    mock_client.delete.assert_called_once_with("films:test_key")


@pytest.mark.unit
def test_mocker_spy_and_stub_demonstration(mocker: MockerFixture, sample_film: Film) -> None:
    """
    Requirement 5: Demonstrate mocker.spy and mocker.stub from pytest-mock.
    - mocker.spy wraps a real function while tracking calls and arguments
    - mocker.stub creates a lightweight callable stub
    """
    # Spy on FilmService._serialize_film
    spy_serialize = mocker.spy(FilmService, "_serialize_film")

    serialized = FilmService._serialize_film(sample_film)

    # Spy assertions
    spy_serialize.assert_called_once_with(sample_film)
    assert spy_serialize.call_count == 1
    assert serialized["title"] == "Interstellar"

    # Stub demonstration: lightweight callable without implementation
    stub_callback = mocker.stub(name="on_cache_miss_stub")
    stub_callback("films:interstellar", reason="not_in_cache")

    stub_callback.assert_called_once_with("films:interstellar", reason="not_in_cache")
    assert stub_callback.call_count == 1


# ===========================================================================
# 4. In-Memory FakeRedis Integration Test (No Live Redis Server Needed)
# ===========================================================================


@pytest.mark.redis
@pytest.mark.integration
async def test_redis_service_with_fakeredis_real_cache_flow(
    fake_redis,
    sample_film: Film,
    mocker: MockerFixture,
) -> None:
    """
    Demonstrate testing Redis using 'fakeredis', an in-memory Redis emulator.
    Unlike mocks, this executes the real Redis protocol, commands, TTLs,
    and serialization without requiring an external Redis server or Docker.
    """
    redis_service = RedisService(client=fake_redis)
    mock_dao = mocker.MagicMock(spec=FilmDAO)
    mock_dao.get_by_id = mocker.AsyncMock(return_value=sample_film)
    mock_session = mocker.MagicMock(spec=AsyncSession)

    service = FilmService(dao=mock_dao, redis_service=redis_service)
    cache_key = f"film:{sample_film.id}"

    # Step 1: Initial call is a CACHE MISS -> queries database and populates fake_redis
    film_1 = await service.get_by_id(session=mock_session, film_id=sample_film.id)
    assert film_1.title == "Interstellar"
    assert mock_dao.get_by_id.call_count == 1

    # Verify key was physically written into in-memory Redis
    exists = await fake_redis.exists(cache_key)
    assert exists == 1

    # Step 2: Second call is a CACHE HIT -> returned directly from in-memory fake_redis
    film_2 = await service.get_by_id(session=mock_session, film_id=sample_film.id)
    assert film_2.title == "Interstellar"
    # DAO call count did NOT increase
    assert mock_dao.get_by_id.call_count == 1

    # Step 3: Invalidate cache
    await redis_service.delete(cache_key)
    assert await fake_redis.exists(cache_key) == 0

