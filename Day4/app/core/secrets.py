"""
AWS Secrets Manager Client & Retrieval Module
=============================================
This module is the single, centralized place for all communication with
AWS Secrets Manager in the Film Review Platform.

Beginner-friendly Architecture Rules:
-------------------------------------
1. This is the ONLY file in the entire project that imports `boto3`.
2. This is the ONLY file that creates an AWS Secrets Manager client.
3. This is the ONLY file that makes API calls to AWS Secrets Manager.
4. No passwords, token secrets, or API keys are hardcoded in application source.
   Local-only values may be loaded from the ignored .env file.
5. If a required secret cannot be retrieved, clear, descriptive errors are raised
   to stop the application immediately at startup.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import boto3
from botocore.exceptions import (
    ClientError,
    EndpointConnectionError,
    NoCredentialsError,
)

logger = logging.getLogger("film_review.core.secrets")

# Cached Secrets Manager client singleton
_secrets_client = None


def reset_secrets_client() -> None:
    """Reset the cached client singleton (useful for testing or credential rotation)."""
    global _secrets_client
    _secrets_client = None


def get_secrets_manager_client(
    region_name: str | None = None,
    endpoint_url: str | None = None,
) -> Any:
    """
    Create or return a reusable boto3 client for AWS Secrets Manager.

    Parameters:
    - region_name: The AWS region. When omitted, boto3 uses its standard configuration chain.
    - endpoint_url: Optional custom URL for local simulation (e.g. Floci / LocalStack: "http://localhost:4566").
    """
    global _secrets_client
    if _secrets_client is not None:
        return _secrets_client

    client_kwargs: dict[str, Any] = {}
    if region_name:
        client_kwargs["region_name"] = region_name

    if endpoint_url:
        client_kwargs["endpoint_url"] = endpoint_url

    logger.info("Initializing AWS Secrets Manager client (region=%s, endpoint=%s)", region_name, endpoint_url)
    _secrets_client = boto3.client("secretsmanager", **client_kwargs)
    return _secrets_client


def get_secret(
    secret_name: str,
    region_name: str | None = None,
    endpoint_url: str | None = None,
) -> dict[str, Any] | str:
    """
    Fetch a secret by name from AWS Secrets Manager.

    - If the secret is stored as a JSON string, returns a parsed dictionary.
    - If stored as plain text, returns the raw string.
    - If the secret does not exist, access is denied, AWS is unreachable,
      or any other retrieval error occurs, raises a descriptive RuntimeError.
    """
    client = get_secrets_manager_client(region_name=region_name, endpoint_url=endpoint_url)

    try:
        response = client.get_secret_value(SecretId=secret_name)
    except ClientError as error:
        error_code = error.response.get("Error", {}).get("Code", "UnknownError")
        error_message = error.response.get("Error", {}).get("Message", str(error))

        if error_code == "ResourceNotFoundException":
            reason = f"Secret '{secret_name}' does not exist in AWS Secrets Manager."
        elif error_code == "AccessDeniedException":
            reason = f"Access denied. IAM credentials lack permission to read secret '{secret_name}'."
        else:
            reason = f"AWS ClientError [{error_code}]: {error_message}"

        fatal_msg = (
            f"FATAL: Application startup failed. Could not retrieve required secret "
            f"'{secret_name}' from AWS Secrets Manager. Reason: {reason}"
        )
        logger.critical(fatal_msg)
        raise RuntimeError(fatal_msg) from error

    except EndpointConnectionError as error:
        target_endpoint = endpoint_url or "AWS default endpoint"
        reason = (
            f"Cannot connect to AWS Secrets Manager endpoint at '{target_endpoint}'. "
            f"Please verify network connectivity or ensure your local AWS simulator is running."
        )
        fatal_msg = (
            f"FATAL: Application startup failed. Could not retrieve required secret "
            f"'{secret_name}' from AWS Secrets Manager. Reason: {reason}"
        )
        logger.critical(fatal_msg)
        raise RuntimeError(fatal_msg) from error

    except NoCredentialsError as error:
        reason = "No AWS credentials found. Please configure AWS credentials or an IAM role."
        fatal_msg = (
            f"FATAL: Application startup failed. Could not retrieve required secret "
            f"'{secret_name}' from AWS Secrets Manager. Reason: {reason}"
        )
        logger.critical(fatal_msg)
        raise RuntimeError(fatal_msg) from error

    except Exception as error:
        reason = f"Unexpected retrieval failure: {str(error)}"
        fatal_msg = (
            f"FATAL: Application startup failed. Could not retrieve required secret "
            f"'{secret_name}' from AWS Secrets Manager. Reason: {reason}"
        )
        logger.critical(fatal_msg)
        raise RuntimeError(fatal_msg) from error

    secret_string = response.get("SecretString")
    if not secret_string:
        fatal_msg = (
            f"FATAL: Application startup failed. Secret '{secret_name}' exists "
            f"but contains an empty or binary payload without SecretString."
        )
        logger.critical(fatal_msg)
        raise RuntimeError(fatal_msg)

    # Attempt to parse as JSON; if not JSON, return plain string
    try:
        parsed = json.loads(secret_string)
        if isinstance(parsed, dict):
            return parsed
        return str(parsed)
    except json.JSONDecodeError:
        return secret_string


def load_application_credentials(
    secret_name: str,
    region_name: str | None = None,
    endpoint_url: str | None = None,
) -> dict[str, str]:
    """
    High-level beginner-friendly helper that loads and validates all required
    application secrets from a JSON secret in AWS Secrets Manager:
    - database_password
    - token_secret_key
    - notification_api_key (optional third-party key)
    - smtp_password (optional SMTP credential)

    Raises a descriptive RuntimeError if any required credential is missing inside the secret.
    """
    secret_data = get_secret(secret_name, region_name=region_name, endpoint_url=endpoint_url)

    if not isinstance(secret_data, dict):
        fatal_msg = (
            f"FATAL: Application startup failed. Secret '{secret_name}' must be formatted "
            f"as a JSON key-value object containing sensitive credentials."
        )
        logger.critical(fatal_msg)
        raise RuntimeError(fatal_msg)

    # 1. Database password (supports common casing conventions)
    db_password = (
        secret_data.get("database_password")
        or secret_data.get("DB_PASSWORD")
        or secret_data.get("password")
    )
    if not db_password:
        fatal_msg = (
            f"FATAL: Application startup failed. Secret '{secret_name}' is missing "
            f"the required 'database_password' credential."
        )
        logger.critical(fatal_msg)
        raise RuntimeError(fatal_msg)

    # 2. JWT signing secret
    jwt_secret = (
        secret_data.get("jwt_secret_key")
        or secret_data.get("JWT_SECRET_KEY")
        or secret_data.get("token_secret_key")
        or secret_data.get("TOKEN_SECRET_KEY")
        or secret_data.get("jwt_secret")
    )
    if not jwt_secret:
        fatal_msg = (
            f"FATAL: Application startup failed. Secret '{secret_name}' is missing "
            f"the required 'token_secret_key' credential."
        )
        logger.critical(fatal_msg)
        raise RuntimeError(fatal_msg)

    # 3. Third-party notification API key
    notification_key = (
        secret_data.get("notification_api_key")
        or secret_data.get("NOTIFICATION_API_KEY")
        or secret_data.get("api_key")
    )

    # 4. Optional credentials
    smtp_password = secret_data.get("smtp_password") or secret_data.get("SMTP_PASSWORD") or ""
    redis_password = secret_data.get("redis_password") or secret_data.get("REDIS_PASSWORD") or ""

    logger.info("Successfully loaded sensitive credentials from AWS Secrets Manager ('%s')", secret_name)

    return {
        "database_password": str(db_password),
        "jwt_secret_key": str(jwt_secret),
        "token_secret_key": str(jwt_secret),
        "notification_api_key": str(notification_key) if notification_key is not None else "",
        "smtp_password": str(smtp_password),
        "redis_password": str(redis_password),
    }
