from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from scripts import init_floci


@pytest.fixture
def floci_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for key, value in {
        "AWS_REGION": "us-east-1",
        "AWS_ENDPOINT_URL": "http://floci:4566",
        "AWS_ACCESS_KEY_ID": "test",
        "AWS_SECRET_ACCESS_KEY": "test",
        "AWS_SECRETS_NAME": "film-review/credentials",
        "S3_BUCKET_NAME": "film-review-storage",
        "SQS_QUEUE_NAME": "film-review-events",
        "S3_CORS_ALLOWED_ORIGINS": "http://localhost:3000,http://localhost:8000",
        "POSTGRES_PASSWORD": "film_secret_pass",
        "LOCAL_TOKEN_SECRET_KEY": "film-review-platform-local-development-signing-key",
        "LOCAL_NOTIFICATION_API_KEY": "local-notification-test-key",
    }.items():
        monkeypatch.setenv(key, value)


@pytest.mark.unit
def test_initializes_missing_secret_and_bucket(floci_environment: None) -> None:
    secrets_client = MagicMock()
    secrets_client.get_secret_value.side_effect = ClientError(
        {"Error": {"Code": "ResourceNotFoundException"}}, "GetSecretValue"
    )
    s3_client = MagicMock()
    s3_client.head_bucket.side_effect = ClientError(
        {"Error": {"Code": "404"}}, "HeadBucket"
    )
    sqs_client = MagicMock()
    sqs_client.create_queue.return_value = {"QueueUrl": "http://floci:4566/000000000000/film-review-events"}

    with (
        patch("scripts.init_floci._wait_for_floci"),
        patch("scripts.init_floci.boto3.client", side_effect=[secrets_client, s3_client, sqs_client]),
    ):
        init_floci.main()

    created_secret = json.loads(secrets_client.create_secret.call_args.kwargs["SecretString"])
    assert created_secret["database_password"] == "film_secret_pass"
    assert created_secret["token_secret_key"].startswith("film-review-platform")
    secrets_client.create_secret.assert_called_once()
    assert secrets_client.create_secret.call_args.kwargs["Name"] == "film-review/credentials"
    s3_client.create_bucket.assert_called_once_with(Bucket="film-review-storage")
    cors_rule = s3_client.put_bucket_cors.call_args.kwargs["CORSConfiguration"]["CORSRules"][0]
    assert cors_rule["AllowedOrigins"] == ["http://localhost:3000", "http://localhost:8000"]
    assert "GET" in cors_rule["AllowedMethods"]
    assert "HEAD" in cors_rule["AllowedMethods"]
    assert "PUT" in cors_rule["AllowedMethods"]
    assert "POST" not in cors_rule["AllowedMethods"]
    sqs_client.create_queue.assert_called_once_with(QueueName="film-review-events")
    sqs_client.get_queue_attributes.assert_called_once_with(
        QueueUrl="http://floci:4566/000000000000/film-review-events",
        AttributeNames=["QueueArn"],
    )


@pytest.mark.unit
def test_preserves_existing_secret_and_bucket(floci_environment: None) -> None:
    secret_string = json.dumps(
        {
            "database_password": "film_secret_pass",
            "token_secret_key": "film-review-platform-local-development-signing-key",
            "notification_api_key": "local-notification-test-key",
        }
    )
    secrets_client = MagicMock()
    secrets_client.get_secret_value.return_value = {"SecretString": secret_string}
    s3_client = MagicMock()
    sqs_client = MagicMock()
    sqs_client.create_queue.return_value = {"QueueUrl": "http://floci:4566/000000000000/film-review-events"}

    with (
        patch("scripts.init_floci._wait_for_floci"),
        patch("scripts.init_floci.boto3.client", side_effect=[secrets_client, s3_client, sqs_client]),
    ):
        init_floci.main()

    secrets_client.create_secret.assert_not_called()
    secrets_client.put_secret_value.assert_not_called()
    s3_client.create_bucket.assert_not_called()
    sqs_client.create_queue.assert_called_once_with(QueueName="film-review-events")
