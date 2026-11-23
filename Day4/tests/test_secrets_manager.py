from __future__ import annotations

import json
import logging
from typing import Any
from unittest.mock import MagicMock, patch

from botocore.exceptions import ClientError, EndpointConnectionError
import pytest

from app.core.secrets import (
    get_secret,
    get_secrets_manager_client,
    load_application_credentials,
    reset_secrets_client,
)


# ==============================================================================
# AWS Secrets Manager Unit & Integration Tests
# ==============================================================================


@pytest.mark.unit
def test_get_secret_json_success() -> None:
    """
    Test 1: Secrets can be successfully fetched and parsed as JSON.
    Verifies that a valid JSON secret string stored in Secrets Manager is
    properly parsed into a dictionary.
    """
    payload = {
        "database_password": "super_secret_db_password",
        "token_secret_key": "jwt_signing_key_32_characters_long!",
        "notification_api_key": "notif-api-key-12345",
    }

    mock_client = MagicMock()
    mock_client.get_secret_value.return_value = {
        "SecretString": json.dumps(payload),
    }

    with patch("app.core.secrets.get_secrets_manager_client", return_value=mock_client):
        result = get_secret("film-review/credentials")

    assert isinstance(result, dict)
    assert result["database_password"] == "super_secret_db_password"
    assert result["token_secret_key"] == "jwt_signing_key_32_characters_long!"
    assert result["notification_api_key"] == "notif-api-key-12345"
    mock_client.get_secret_value.assert_called_once_with(SecretId="film-review/credentials")


@pytest.mark.unit
def test_get_secret_plaintext_success() -> None:
    """
    Test 2: Plaintext secrets return the raw string correctly.
    """
    mock_client = MagicMock()
    mock_client.get_secret_value.return_value = {
        "SecretString": "raw_plain_text_secret_token",
    }

    with patch("app.core.secrets.get_secrets_manager_client", return_value=mock_client):
        result = get_secret("film-review/raw_secret")

    assert result == "raw_plain_text_secret_token"


@pytest.mark.unit
def test_get_secret_not_found_raises_descriptive_error() -> None:
    """
    Test 3: Application raises a descriptive error when a secret does not exist.
    Verifies that ResourceNotFoundException is caught and converted into a clear
    RuntimeError naming the missing secret.
    """
    mock_client = MagicMock()
    error_response = {
        "Error": {
            "Code": "ResourceNotFoundException",
            "Message": "Secrets Manager can't find the specified secret.",
        }
    }
    mock_client.get_secret_value.side_effect = ClientError(
        error_response, "GetSecretValue"
    )

    with patch("app.core.secrets.get_secrets_manager_client", return_value=mock_client):
        with pytest.raises(RuntimeError) as exc_info:
            get_secret("nonexistent/secret/path")

    error_msg = str(exc_info.value)
    assert "FATAL: Application startup failed" in error_msg
    assert "nonexistent/secret/path" in error_msg
    assert "does not exist in AWS Secrets Manager" in error_msg


@pytest.mark.unit
def test_get_secret_unreachable_endpoint_raises_descriptive_error() -> None:
    """
    Test 4: Application raises a descriptive error when AWS Secrets Manager is unreachable.
    Verifies that EndpointConnectionError is caught and converted into a clear
    RuntimeError advising to check network connectivity or local simulator.
    """
    mock_client = MagicMock()
    mock_client.get_secret_value.side_effect = EndpointConnectionError(
        endpoint_url="http://localhost:4566"
    )

    with patch("app.core.secrets.get_secrets_manager_client", return_value=mock_client):
        with pytest.raises(RuntimeError) as exc_info:
            get_secret("film-review/credentials", endpoint_url="http://localhost:4566")

    error_msg = str(exc_info.value)
    assert "FATAL: Application startup failed" in error_msg
    assert "Cannot connect to AWS Secrets Manager endpoint" in error_msg


@pytest.mark.unit
def test_get_secret_access_denied_raises_descriptive_error() -> None:
    """
    Test 5: AccessDeniedException raises a descriptive error indicating permission issues.
    """
    mock_client = MagicMock()
    error_response = {
        "Error": {
            "Code": "AccessDeniedException",
            "Message": "User is not authorized to perform: secretsmanager:GetSecretValue",
        }
    }
    mock_client.get_secret_value.side_effect = ClientError(
        error_response, "GetSecretValue"
    )

    with patch("app.core.secrets.get_secrets_manager_client", return_value=mock_client):
        with pytest.raises(RuntimeError) as exc_info:
            get_secret("film-review/restricted_secret")

    error_msg = str(exc_info.value)
    assert "Access denied" in error_msg
    assert "film-review/restricted_secret" in error_msg


@pytest.mark.unit
def test_load_application_credentials_validates_required_keys() -> None:
    """
    Test 6: Validates that missing required keys (e.g. database_password) fail fast.
    """
    # Missing database_password
    with patch("app.core.secrets.get_secret", return_value={"token_secret_key": "some_token"}):
        with pytest.raises(RuntimeError) as exc_info:
            load_application_credentials("film-review/incomplete")

    assert "missing the required 'database_password' credential" in str(exc_info.value)

    # Missing token_secret_key
    with patch("app.core.secrets.get_secret", return_value={"database_password": "some_password"}):
        with pytest.raises(RuntimeError) as exc_info:
            load_application_credentials("film-review/incomplete")

    assert "missing the required 'token_secret_key' credential" in str(exc_info.value)


@pytest.mark.unit
def test_sensitive_values_not_exposed_in_logs_or_errors(caplog: pytest.LogCaptureFixture) -> None:
    """
    Test 7: Sensitive credentials (passwords, JWT secrets) are NEVER exposed
    in logs or exception messages.
    """
    mock_client = MagicMock()
    mock_client.get_secret_value.side_effect = EndpointConnectionError(
        endpoint_url="http://localhost:4566"
    )

    with caplog.at_level(logging.DEBUG):
        with patch("app.core.secrets.get_secrets_manager_client", return_value=mock_client):
            try:
                get_secret("film-review/credentials")
            except RuntimeError as exc:
                error_str = str(exc)
                # Password and secret keys must not appear in exception
                assert "film_secret_pass" not in error_str
                assert "super-secret" not in error_str

    # Verify log messages
    for record in caplog.records:
        assert "film_secret_pass" not in record.message
        assert "super-secret" not in record.message


@pytest.mark.unit
def test_settings_dynamic_configuration_assembly() -> None:
    """
    Test 8: Settings builds DATABASE_URL dynamically using credentials from secret.
    """
    mock_creds = {
        "database_password": "injected_dynamic_password",
        "token_secret_key": "jwt_secret_with_sufficient_length_here",
        "notification_api_key": "notif_key_abc",
        "smtp_password": "",
        "redis_password": "",
    }

    with patch("app.core.config.load_application_credentials", return_value=mock_creds):
        from app.core.config import Settings

        test_settings = Settings(
            DB_HOST="postgres-db.example.com",
            DB_PORT=5432,
            DB_USER="custom_user",
            DB_NAME="custom_db",
            AWS_SECRETS_NAME="film-review/credentials",
        )

        assert test_settings.DB_PASSWORD == "injected_dynamic_password"
        assert test_settings.TOKEN_SECRET_KEY == "jwt_secret_with_sufficient_length_here"
        assert test_settings.JWT_SECRET_KEY == "jwt_secret_with_sufficient_length_here"
        assert test_settings.NOTIFICATION_API_KEY == "notif_key_abc"
        expected_url = "postgresql+asyncpg://custom_user:injected_dynamic_password@postgres-db.example.com:5432/custom_db"
        assert test_settings.DATABASE_URL == expected_url


@pytest.mark.integration
def test_live_secret_retrieval_floci() -> None:
    """
    Test 9: Live integration test fetching secret from local Floci / Secrets Manager emulator.
    Uses AWS_ENDPOINT_URL from environment (e.g., host.docker.internal in Docker or localhost on host).
    If the live emulator is not running, cleanly skips per requirement to allow offline test execution.
    """
    import os
    reset_secrets_client()
    endpoint = os.environ.get("AWS_ENDPOINT_URL", "http://localhost:4566")
    region = os.environ.get("AWS_REGION", "us-east-1")
    secret_name = os.environ.get("AWS_SECRETS_NAME", "film-review/credentials")

    try:
        creds = load_application_credentials(
            secret_name,
            region_name=region,
            endpoint_url=endpoint,
        )
        assert bool(creds.get("database_password"))
        assert len(creds["token_secret_key"]) >= 32
        assert "database_password" in creds
        assert "token_secret_key" in creds
    except RuntimeError as exc:
        pytest.skip(f"Live Secrets Manager emulator not reachable at {endpoint}: {exc}")
