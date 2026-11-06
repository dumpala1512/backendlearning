from __future__ import annotations

from datetime import date, datetime, timezone
import json
import uuid
from httpx import AsyncClient
from pydantic import BaseModel
import pytest
from pytest_mock import MockerFixture
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, create_refresh_token
from app.dao.film_dao import FilmDAO
from app.dao.review_dao import ReviewDAO
from app.exceptions.film import FilmNotFoundError
from app.exceptions.review import ReviewNotFoundError, ReviewPermissionDeniedError
from app.exceptions.user import TokenRevokedError
from app.models.film import Film
from app.models.review import Review
from app.schemas.film import FilmFilterQuery
from app.services.film_service import FilmService
from app.services.redis_service import CustomJSONEncoder, RedisService
from app.services.review_service import ReviewService
from app.services.user_service import UserService
from tests.helpers import get_auth_headers, get_user_headers


# ===========================================================================
# Branch 1: Redis Cache Hit Branches in list_films and list_films_paginated
# ===========================================================================


@pytest.mark.unit
@pytest.mark.redis
async def test_list_films_cache_hit_branch(mocker: MockerFixture) -> None:
    """
    Branch 1A: FilmService.list_films cache hit branch.
    Previously uncovered because tests ran without pre-populating list cache in Redis.
    """
    cached_payload = [
        {
            "id": str(uuid.uuid4()),
            "title": "Cached Sci-Fi Movie",
            "director": "Jane Director",
            "release_year": 2021,
            "genre": "Sci-Fi",
            "description": "Cached description.",
            "is_active": True,
            "created_at": "2026-01-01T00:00:00Z",
        }
    ]

    mock_redis = mocker.MagicMock(spec=RedisService)
    mock_redis.get = mocker.AsyncMock(return_value=cached_payload)
    mock_dao = mocker.MagicMock(spec=FilmDAO)
    mock_dao.list_films = mocker.AsyncMock()

    service = FilmService(dao=mock_dao, redis_service=mock_redis)
    mock_session = mocker.MagicMock(spec=AsyncSession)

    result = await service.list_films(session=mock_session, genre="Sci-Fi")

    # Assert cache hit bypassed DAO
    mock_redis.get.assert_called_once()
    mock_dao.list_films.assert_not_called()
    assert len(result) == 1
    assert result[0].title == "Cached Sci-Fi Movie"


@pytest.mark.unit
@pytest.mark.redis
async def test_list_films_paginated_cache_hit_branch(mocker: MockerFixture) -> None:
    """
    Branch 1B: FilmService.list_films_paginated cache hit branch.
    """
    cached_data = {
        "page": 1,
        "limit": 10,
        "total": 1,
        "total_pages": 1,
        "items": [
            {
                "id": str(uuid.uuid4()),
                "title": "Cached Paginated Movie",
                "director": "John Director",
                "release_year": 2022,
                "genre": "Drama",
                "description": "Cached paginated description.",
                "is_active": True,
                "created_at": "2026-01-01T00:00:00Z",
            }
        ],
    }

    mock_redis = mocker.MagicMock(spec=RedisService)
    mock_redis.get = mocker.AsyncMock(return_value=cached_data)
    mock_dao = mocker.MagicMock(spec=FilmDAO)
    mock_dao.list_films_paginated = mocker.AsyncMock()

    service = FilmService(dao=mock_dao, redis_service=mock_redis)
    mock_session = mocker.MagicMock(spec=AsyncSession)

    response = await service.list_films_paginated(session=mock_session, genre="Drama")

    mock_redis.get.assert_called_once()
    mock_dao.list_films_paginated.assert_not_called()
    assert response.total == 1
    assert response.items[0].title == "Cached Paginated Movie"


# ===========================================================================
# Branch 2: Redis Service Error Handling & Pattern Deletion
# ===========================================================================


@pytest.mark.unit
@pytest.mark.redis
async def test_redis_service_error_handling_branches(mocker: MockerFixture) -> None:
    """
    Branch 2A: RedisService error branches when RedisError occurs on get, set, delete.
    Ensures graceful failure (returns None / False, never crashes application).
    """
    mock_client = mocker.AsyncMock()
    mock_client.get = mocker.AsyncMock(side_effect=RedisError("Connection refused"))
    mock_client.set = mocker.AsyncMock(side_effect=RedisError("Write failure"))
    mock_client.delete = mocker.AsyncMock(side_effect=RedisError("Delete failure"))

    redis_service = RedisService(client=mock_client)

    # get() on RedisError returns None gracefully
    get_res = await redis_service.get("some_key")
    assert get_res is None

    # set() on RedisError returns False gracefully
    set_res = await redis_service.set("some_key", {"data": 123})
    assert set_res is False

    # delete() on RedisError returns False gracefully
    del_res = await redis_service.delete("some_key")
    assert del_res is False


@pytest.mark.unit
@pytest.mark.redis
async def test_redis_service_delete_by_pattern_and_scan(mocker: MockerFixture) -> None:
    """
    Branch 2B: RedisService.delete_by_pattern with matching keys and when no client exists.
    """
    # Case with matching keys
    mock_client = mocker.AsyncMock()

    async def fake_scan(match: str):
        for k in ["films:list:1", "films:list:2"]:
            yield k

    mock_client.scan_iter = fake_scan
    mock_client.delete = mocker.AsyncMock(return_value=2)

    redis_service = RedisService(client=mock_client)
    deleted_count = await redis_service.delete_by_pattern("films:list*")
    assert deleted_count == 2
    mock_client.delete.assert_called_once_with("films:list:1", "films:list:2")

    # Case when client is None
    no_cli_service = RedisService(client=None)
    # mock get_redis_client to return None
    mocker.patch("app.services.redis_service.get_redis_client", return_value=None)
    assert await no_cli_service.delete_by_pattern("films:*") == 0
    assert await no_cli_service.exists("films:key") is False


# ===========================================================================
# Branch 3: Custom JSON Encoder Serialization Primitives
# ===========================================================================


class DemoModel(BaseModel):
    name: str
    count: int


@pytest.mark.unit
def test_custom_json_encoder_branches() -> None:
    """
    Branch 3: CustomJSONEncoder branches for datetime, date, UUID, BaseModel, and sets.
    """
    now = datetime(2026, 5, 1, 10, 0, 0, tzinfo=timezone.utc)
    today = date(2026, 5, 1)
    test_uuid = uuid.UUID("abcdef01-2345-6789-abcd-ef0123456789")
    model = DemoModel(name="test", count=42)
    sample_set = {"tag1", "tag2"}

    payload = {
        "dt": now,
        "d": today,
        "uid": test_uuid,
        "model": model,
        "tags": sample_set,
    }

    serialized = json.dumps(payload, cls=CustomJSONEncoder)
    data = json.loads(serialized)

    assert data["dt"] == "2026-05-01T10:00:00+00:00"
    assert data["d"] == "2026-05-01"
    assert data["uid"] == "abcdef01-2345-6789-abcd-ef0123456789"
    assert data["model"] == {"name": "test", "count": 42}
    assert set(data["tags"]) == {"tag1", "tag2"}


# ===========================================================================
# Branch 4: Token Refresh Endpoint & Revocation Checks
# ===========================================================================


@pytest.mark.integration
@pytest.mark.redis
async def test_token_refresh_and_revocation_branches(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """
    Branch 4: POST /refresh and /auth/refresh with valid, revoked, and malformed tokens.
    """
    # 1. Register user
    username = "token_tester"
    email = "token_tester@example.com"
    raw_pass = "SecurePass123!"

    reg = await client.post(
        "/api/v1/register",
        json={"username": username, "email": email, "password": raw_pass, "confirm_password": raw_pass},
    )
    assert reg.status_code == 201

    # 2. Login to obtain access and refresh tokens
    login_res = await client.post("/login", json={"username": username, "password": raw_pass})
    assert login_res.status_code == 200
    tokens = login_res.json()
    refresh_token = tokens["refresh_token"]

    # 3. Valid refresh -> returns new access token
    refresh_res = await client.post("/refresh", json={"refresh_token": refresh_token})
    assert refresh_res.status_code == 200
    data = refresh_res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

    # 4. Refresh with malformed token -> 401 Unauthorized
    bad_res = await client.post("/refresh", json={"refresh_token": "malformed.invalid.token"})
    assert bad_res.status_code == 401

    # 5. Logout
    access_token = data["access_token"]
    logout_res = await client.post("/logout", headers=get_auth_headers(access_token))
    assert logout_res.status_code == 200

    # 6. Refresh after logout -> 401 Revoked
    revoked_res = await client.post("/refresh", json={"refresh_token": refresh_token})
    assert revoked_res.status_code == 401


# ===========================================================================
# Branch 5: Review Update & Delete Author RBAC
# ===========================================================================


@pytest.mark.integration
async def test_review_update_and_delete_author_rbac(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """
    Branch 5: Review update and delete endpoints verifying:
    - Original author can update review (200)
    - Non-author user attempting update is rejected (403 ReviewPermissionDenied)
    - Non-author viewer attempting delete is rejected (403)
    - Original author can delete review (200)
    """
    author_headers = await get_user_headers(client, db_session, role="critic", username="critic_author_1")
    other_critic_headers = await get_user_headers(client, db_session, role="critic", username="critic_other_2")
    admin_headers = await get_user_headers(client, db_session, role="admin", username="admin_for_film")

    # Create film
    film_res = await client.post(
        "/films",
        headers=admin_headers,
        json={
            "title": "Pulp Fiction",
            "director": "Quentin Tarantino",
            "release_year": 1994,
            "genre": "Crime",
            "description": "The lives of two mob hitmen, a boxer, and a gangster and his wife intertwine.",
        },
    )
    film_id = film_res.json()["id"]

    # Author creates review
    rev_res = await client.post(
        f"/films/{film_id}/reviews",
        headers=author_headers,
        json={
            "film_id": film_id,
            "rating": 9,
            "review": "A masterpiece of non-linear storytelling with iconic dialogue and soundtrack.",
            "reviewer_display_name": "Author Critic",
        },
    )
    assert rev_res.status_code == 201
    review_id = rev_res.json()["id"]

    # Unauthorized critic attempts update -> 403 Forbidden
    unauth_patch = await client.patch(
        f"/reviews/{review_id}",
        headers=other_critic_headers,
        json={"rating": 1, "review": "Maliciously updated review text that is long enough to pass validation."},
    )
    assert unauth_patch.status_code == 403
    assert unauth_patch.json()["type"] == "ReviewPermissionDenied"

    # Authorized original author updates review -> 200 OK
    auth_patch = await client.patch(
        f"/reviews/{review_id}",
        headers=author_headers,
        json={"rating": 10, "review": "Updated review rating to perfection after a second theatrical viewing."},
    )
    assert auth_patch.status_code == 200
    assert auth_patch.json()["rating"] == 10

    # Unauthorized critic attempts delete -> 403 Forbidden
    unauth_del = await client.delete(f"/reviews/{review_id}", headers=other_critic_headers)
    assert unauth_del.status_code == 403
    assert unauth_del.json()["type"] == "ReviewPermissionDenied"

    # Authorized author deletes review -> 200 OK
    auth_del = await client.delete(f"/reviews/{review_id}", headers=author_headers)
    assert auth_del.status_code == 200
    assert auth_del.json()["success"] is True


# ===========================================================================
# Branch 6: Film Service Edge Cases (Non-existent film update/delete)
# ===========================================================================


@pytest.mark.unit
async def test_film_service_missing_film_branches(mocker: MockerFixture) -> None:
    """
    Branch 6: FilmService.update_film and delete_film raising FilmNotFoundError.
    """
    mock_dao = mocker.MagicMock(spec=FilmDAO)
    mock_dao.update = mocker.AsyncMock(return_value=None)
    mock_dao.get_by_id = mocker.AsyncMock(return_value=None)

    service = FilmService(dao=mock_dao, redis_service=None)
    mock_session = mocker.MagicMock(spec=AsyncSession)
    missing_id = uuid.uuid4()

    # update_film on missing film raises FilmNotFoundError
    with pytest.raises(FilmNotFoundError) as exc_up:
        await service.update_film(session=mock_session, film_id=missing_id, title="New Title")
    assert exc_up.value.resource_id == missing_id

    # delete_film on missing film raises FilmNotFoundError
    with pytest.raises(FilmNotFoundError) as exc_del:
        await service.delete_film(session=mock_session, film_id=missing_id)
    assert exc_del.value.resource_id == missing_id
