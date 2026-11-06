from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
import pytest
from pytest_mock import MockerFixture

from app.services.notification_service import NotificationService


# ===========================================================================
# Requirement 8: Third-Party Service Mock Tests
# ===========================================================================


@pytest.mark.unit
async def test_third_party_notification_service_using_mocker(mocker: MockerFixture) -> None:
    """
    Requirement 8: Third-party service mock using pytest-mock `mocker`.

    Verifies:
    - External notification service invoked
    - Correct payload sent (recipient, film_title, rating, template)
    - Correct authorization header sent
    - No actual network request is performed
    - AsyncMock handles the awaitable response
    """
    # 1. Arrange mock response
    expected_response_data = {
        "status": "delivered",
        "message_id": "msg-xyz-987654",
        "recipient": "critic@example.com",
    }
    mock_response = mocker.MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = expected_response_data
    mock_response.raise_for_status = mocker.MagicMock()

    # 2. Mock httpx.AsyncClient.post with AsyncMock
    mock_post = mocker.patch.object(httpx.AsyncClient, "post", new_callable=mocker.AsyncMock)
    mock_post.return_value = mock_response

    # 3. Instantiate service
    service = NotificationService(
        api_url="https://api.notifications.example.com",
        api_key="mock-api-key-12345",
    )

    # 4. Act
    result = await service.send_review_notification(
        recipient_email="critic@example.com",
        film_title="Dune: Part Two",
        rating=10,
    )

    # 5. Assert: Service invoked exactly once
    mock_post.assert_called_once()
    assert mock_post.call_count == 1

    # 6. Assert: Correct endpoint URL and payload sent
    called_url = mock_post.call_args[0][0]
    called_kwargs = mock_post.call_args[1]

    assert called_url == "https://api.notifications.example.com/v1/notifications/review"
    assert called_kwargs["json"] == {
        "recipient": "critic@example.com",
        "film_title": "Dune: Part Two",
        "rating": 10,
        "template": "new_review_alert",
    }
    assert called_kwargs["headers"]["Authorization"] == "Bearer mock-api-key-12345"
    assert called_kwargs["timeout"] == 5.0

    # 7. Assert: Response data matches expected without hitting external network
    assert result == expected_response_data


@pytest.mark.unit
async def test_third_party_service_using_patch_context_manager() -> None:
    """
    Requirement 5 & 8: Demonstrate unittest.mock.patch as a context manager
    for mocking an external third-party HTTP dependency.
    """
    service = NotificationService(
        api_url="https://api.external-email.com",
        api_key="secret-token-abc",
    )

    fake_response = MagicMock(spec=httpx.Response)
    fake_response.status_code = 202
    fake_response.json.return_value = {"id": "job-123", "status": "queued"}
    fake_response.raise_for_status = MagicMock()

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = fake_response

        data = await service.send_review_notification(
            recipient_email="viewer@example.com",
            film_title="Arrival",
            rating=9,
        )

        # Assertions
        mock_post.assert_called_once()
        assert data["status"] == "queued"
        assert mock_post.call_args[1]["json"]["film_title"] == "Arrival"

    # Context manager has exited: verify httpx.AsyncClient.post is restored
    assert not isinstance(httpx.AsyncClient.post, AsyncMock)


@pytest.mark.unit
def test_sync_third_party_dependency_using_magicmock(mocker: MockerFixture) -> None:
    """
    Requirement 5: Demonstrate MagicMock for synchronous dependencies / external methods.
    """
    mock_service = MagicMock(spec=NotificationService)
    mock_service.get_service_status.return_value = {"status": "ok", "provider": "mock"}

    status_data = mock_service.get_service_status()

    mock_service.get_service_status.assert_called_once()
    assert status_data["status"] == "ok"
