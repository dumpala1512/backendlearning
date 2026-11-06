from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock
from httpx import AsyncClient
import pytest
from pytest_mock import MockerFixture
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis_client
from app.core.security import create_access_token
from app.dependencies import get_user_service
from app.models.user import User
from app.services.redis_service import RedisService
from app.services.user_service import UserService
from tests.helpers import get_auth_headers

# Mark all tests in this file with the 'redis' marker
pytestmark = [pytest.mark.redis]


@pytest.mark.unit
async def test_logout_endpoint_with_mocked_redis_client(
    client: AsyncClient,
    mocker: MockerFixture,
) -> None:
    """
    Requirement 2: Logout Endpoint Test using a Mocked Redis Client.

    The logout endpoint invalidates a user's session by deleting a Redis key.
    Write a test using a mocked Redis client.

    Assertions must verify:
    - delete() called exactly once
    - delete() received the exact session key
    - HTTP response status code (200 OK)
    - Response body ({"message": "Logged out successfully"})
    - Call count and exact arguments
    """
    # 1. Arrange: User credentials and valid JWT access token
    user_id = uuid.uuid4()
    access_token = create_access_token({
        "sub": str(user_id),
        "username": "sarah_connor",
        "role": "critic",
    })
    headers = get_auth_headers(access_token)
    expected_session_key = f"session:{user_id}"

    # 2. Mock low-level Redis client completely
    mock_redis = mocker.AsyncMock()
    mock_redis.delete = mocker.AsyncMock(return_value=1)
    mock_redis.get = mocker.AsyncMock(return_value=None)

    # Override get_redis_client in FastAPI application dependency injection
    from app.main import app
    app.dependency_overrides[get_redis_client] = lambda: mock_redis

    try:
        # 3. Act: Issue POST request to /logout
        response = await client.post("/logout", headers=headers)

        # 4. Assert: Status code and response body
        assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}: {response.text}"
        payload = response.json()
        assert payload == {"message": "Logged out successfully"}

        # 5. Assert: Mock Redis interactions
        mock_redis.delete.assert_called_once_with(expected_session_key)
        assert mock_redis.delete.call_count == 1
        assert mock_redis.delete.call_args[0][0] == expected_session_key

    finally:
        app.dependency_overrides.pop(get_redis_client, None)


@pytest.mark.unit
async def test_logout_endpoint_with_custom_session_id_header(
    client: AsyncClient,
    mocker: MockerFixture,
) -> None:
    """
    Requirement 2 & 6: Test logout with custom session identifier header (X-Session-ID).
    Verifies that the exact session key is passed to delete().
    """
    user_id = uuid.uuid4()
    custom_session_id = f"sess_{uuid.uuid4().hex[:12]}"
    expected_session_key = f"session:{custom_session_id}"

    access_token = create_access_token({
        "sub": str(user_id),
        "username": "kyle_reese",
        "role": "viewer",
    })
    headers = {
        **get_auth_headers(access_token),
        "X-Session-ID": custom_session_id,
    }

    mock_redis = mocker.AsyncMock()
    mock_redis.delete = mocker.AsyncMock(return_value=1)
    mock_redis.get = mocker.AsyncMock(return_value=None)

    from app.main import app
    app.dependency_overrides[get_redis_client] = lambda: mock_redis

    try:
        response = await client.post("/api/v1/auth/logout", headers=headers)

        assert response.status_code == 200
        assert response.json()["message"] == "Logged out successfully"

        # Assert delete() called with exact session key
        mock_redis.delete.assert_called_once_with(expected_session_key)
        assert mock_redis.delete.call_count == 1

    finally:
        app.dependency_overrides.pop(get_redis_client, None)


@pytest.mark.unit
async def test_user_service_logout_unit_direct_mock(mocker: MockerFixture) -> None:
    """
    Direct service-level unit test for UserService.logout verifying mock interactions:
    - RedisService.delete called once with session key
    - RedisService.get called once for user_refresh_tokens
    - Call count and arguments
    """
    user_id = uuid.uuid4()
    session_key = f"session:{user_id}"

    mock_redis_service = mocker.MagicMock(spec=RedisService)
    mock_redis_service.delete = mocker.AsyncMock(return_value=True)
    mock_redis_service.get = mocker.AsyncMock(return_value=None)

    service = UserService(dao=mocker.MagicMock(), redis_service=mock_redis_service)

    # Act
    await service.logout(user_id=user_id)

    # Assert
    mock_redis_service.delete.assert_called_once_with(session_key)
    assert mock_redis_service.delete.call_count == 1
    assert mock_redis_service.get.call_count == 1
