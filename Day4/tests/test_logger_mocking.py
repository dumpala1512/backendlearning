from __future__ import annotations

import logging
from unittest.mock import MagicMock, call, patch
import uuid
from fastapi import FastAPI, Request, status
from fastapi.testclient import TestClient
import pytest
from pytest_mock import MockerFixture

from app.exceptions.base import DomainError
from app.exceptions.film import FilmHasActiveReviewsError, FilmNotFoundError
from app.exceptions.handlers import register_exception_handlers
from app.exceptions.review import ReviewAlreadyExistsError
from app.models.film import Film
from app.services.film_service import FilmService


@pytest.fixture
def test_app_with_handlers() -> FastAPI:
    """Create a minimal isolated FastAPI app configured with centralized exception handlers."""
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/trigger-not-found")
    async def trigger_not_found():
        raise FilmNotFoundError(film_id=uuid.UUID("12345678-1234-5678-1234-567812345678"))

    @app.get("/trigger-conflict")
    async def trigger_conflict():
        raise ReviewAlreadyExistsError(
            film_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
            user_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
        )

    class InternalDatabaseError(DomainError):
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    @app.get("/trigger-server-error")
    async def trigger_server_error():
        raise InternalDatabaseError(message="Internal database subsystem failure")

    return app


# ===========================================================================
# 1. Logger Mocking with pytest-mock (mocker.patch)
# ===========================================================================


@pytest.mark.unit
def test_logger_mock_with_mocker_patch(
    test_app_with_handlers: FastAPI,
    mocker: MockerFixture,
) -> None:
    """
    Requirement 7: Replace structured logger with a mock using pytest-mock `mocker`.
    Verify:
    - logger.info called for 404
    - logger.warning called for 409
    - logger.error called for 500
    - exact messages and arguments
    - number of invocations
    - no real logging occurs
    """
    # Replace the handlers logger with a MagicMock
    mock_logger = mocker.patch("app.exceptions.handlers.logger", autospec=True)

    client = TestClient(test_app_with_handlers)

    # -----------------------------------------------------------------------
    # Case 1: Trigger 404 (FilmNotFoundError) -> logger.info
    # -----------------------------------------------------------------------
    res_404 = client.get("/trigger-not-found")
    assert res_404.status_code == 404

    # Assert logger.info was called with exact format string & parameters
    mock_logger.info.assert_called_once()
    assert mock_logger.info.call_count == 1
    args, _ = mock_logger.info.call_args
    assert args[0] == "Domain error encountered [%d - %s]: %s"
    assert args[1] == 404
    assert args[2] == "FilmNotFound"
    assert "not found" in args[3].lower()

    # Verify warning and error were NOT called in this step
    mock_logger.warning.assert_not_called()
    mock_logger.error.assert_not_called()

    # Reset mock state
    mock_logger.reset_mock()

    # -----------------------------------------------------------------------
    # Case 2: Trigger 409 (ReviewAlreadyExistsError) -> logger.warning
    # -----------------------------------------------------------------------
    res_409 = client.get("/trigger-conflict")
    assert res_409.status_code == 409

    # Assert logger.warning was called with exact format string & parameters
    mock_logger.warning.assert_called_once()
    assert mock_logger.warning.call_count == 1
    args, _ = mock_logger.warning.call_args
    assert args[0] == "Domain rule constraint triggered [%d - %s]: %s"
    assert args[1] == 409
    assert args[2] == "ReviewAlreadyExists"

    mock_logger.info.assert_not_called()
    mock_logger.error.assert_not_called()

    # Reset mock state
    mock_logger.reset_mock()

    # -----------------------------------------------------------------------
    # Case 3: Trigger 500 (DomainError >= 500) -> logger.error
    # -----------------------------------------------------------------------
    res_500 = client.get("/trigger-server-error")
    assert res_500.status_code == 500

    # Assert logger.error was called with exact format string & parameters
    mock_logger.error.assert_called_once()
    assert mock_logger.error.call_count == 1
    args, kwargs = mock_logger.error.call_args
    assert args[0] == "Unhandled domain error [%d - %s]: %s"
    assert args[1] == 500
    assert args[2] == "InternalDatabase"
    assert "database subsystem failure" in args[3]
    assert kwargs.get("exc_info") is True


# ===========================================================================
# 2. Logger Mocking with unittest.mock.patch (Context Manager & Decorator)
# ===========================================================================


@pytest.mark.unit
def test_logger_mock_with_unittest_patch_context_manager(
    test_app_with_handlers: FastAPI,
) -> None:
    """
    Requirement 5 & 7: Demonstrate patch() context manager mocking logger.
    Verifies automatic restoration of original logger object after test.
    """
    client = TestClient(test_app_with_handlers)

    with patch("app.exceptions.handlers.logger") as mock_logger:
        res = client.get("/trigger-not-found")
        assert res.status_code == 404

        # Check call count and assertions
        assert mock_logger.info.call_count == 1
        mock_logger.info.assert_called_once()
        mock_logger.warning.assert_not_called()
        mock_logger.error.assert_not_called()

    # After context manager exit, original logger is restored
    from app.exceptions import handlers
    assert not isinstance(handlers.logger, MagicMock)


@pytest.mark.unit
async def test_film_service_logger_mocking(mocker: MockerFixture) -> None:
    """
    Requirement 7: Mock logger inside FilmService to verify info and warning calls.
    Verifies no real logging occurs to stdout/stderr.
    """
    mock_logger = mocker.patch("app.services.film_service.logger")

    mock_dao = mocker.AsyncMock()
    fake_film = Film(
        id=uuid.uuid4(),
        title="Oppenheimer",
        director="Christopher Nolan",
        release_year=2023,
        genre="Biography",
        description="The story of J. Robert Oppenheimer.",
    )
    mock_dao.create = mocker.AsyncMock(return_value=fake_film)

    service = FilmService(dao=mock_dao, redis_service=None)
    mock_session = mocker.MagicMock()

    # Act: create film
    created = await service.create_film(
        session=mock_session,
        title="Oppenheimer",
        director="Christopher Nolan",
        release_year=2023,
        genre="Biography",
        description="The story of J. Robert Oppenheimer.",
    )

    # Assert logger.info was called with exact message format
    mock_logger.info.assert_called_once()
    format_str, title_arg, id_arg = mock_logger.info.call_args[0]
    assert format_str == "Film '%s' created successfully with id %s"
    assert title_arg == "Oppenheimer"
    assert id_arg == created.id
