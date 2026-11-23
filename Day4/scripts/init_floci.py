from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from dotenv import dotenv_values


def _load_environment() -> None:
    env_file = Path(__file__).resolve().parents[1] / ".env"
    for key, value in dotenv_values(env_file).items():
        if value is not None:
            os.environ.setdefault(key, value)

    required = (
        "AWS_REGION",
        "AWS_ENDPOINT_URL",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SECRETS_NAME",
        "S3_BUCKET_NAME",
        "SQS_QUEUE_NAME",
        "POSTGRES_PASSWORD",
        "LOCAL_TOKEN_SECRET_KEY",
    )
    missing = [key for key in required if not os.environ.get(key)]
    if missing:
        raise RuntimeError(f"Missing required local configuration: {', '.join(missing)}")


def _client(service_name: str) -> Any:
    options: dict[str, Any] = {
        "service_name": service_name,
        "region_name": os.environ["AWS_REGION"],
        "endpoint_url": os.environ["AWS_ENDPOINT_URL"],
        "aws_access_key_id": os.environ["AWS_ACCESS_KEY_ID"],
        "aws_secret_access_key": os.environ["AWS_SECRET_ACCESS_KEY"],
    }
    if service_name == "s3":
        options["config"] = Config(s3={"addressing_style": "path"})
    return boto3.client(**options)


def _wait_for_floci() -> None:
    endpoint = os.environ["AWS_ENDPOINT_URL"].rstrip("/")
    deadline = time.monotonic() + 60
    while True:
        try:
            with urlopen(f"{endpoint}/health", timeout=2) as response:
                if response.status == 200:
                    return
        except URLError:
            pass

        if time.monotonic() >= deadline:
            raise RuntimeError(f"Floci did not become healthy at {endpoint}/health within 60 seconds.")
        time.sleep(1)


def _ensure_secret() -> None:
    client = _client("secretsmanager")
    secret_name = os.environ["AWS_SECRETS_NAME"]
    secret_string = json.dumps(
        {
            "database_password": os.environ["POSTGRES_PASSWORD"],
            "token_secret_key": os.environ["LOCAL_TOKEN_SECRET_KEY"],
            "notification_api_key": os.environ.get("LOCAL_NOTIFICATION_API_KEY", ""),
        }
    )

    try:
        current = client.get_secret_value(SecretId=secret_name)
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code")
        if code != "ResourceNotFoundException":
            raise
        client.create_secret(Name=secret_name, SecretString=secret_string)
        return

    if current.get("SecretString") != secret_string:
        client.put_secret_value(SecretId=secret_name, SecretString=secret_string)


def _ensure_bucket() -> None:
    client = _client("s3")
    bucket_name = os.environ["S3_BUCKET_NAME"]
    try:
        client.head_bucket(Bucket=bucket_name)
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code")
        if code not in {"404", "NoSuchBucket", "NotFound"}:
            raise
        client.create_bucket(Bucket=bucket_name)

    origins = [
        origin.strip()
        for origin in os.environ.get("S3_CORS_ALLOWED_ORIGINS", "").split(",")
        if origin.strip()
    ]
    if origins:
        client.put_bucket_cors(
            Bucket=bucket_name,
            CORSConfiguration={
                "CORSRules": [
                    {
                        "AllowedOrigins": origins,
                        "AllowedMethods": ["PUT", "GET", "HEAD"],
                        "AllowedHeaders": ["*"],
                        "ExposeHeaders": ["ETag"],
                        "MaxAgeSeconds": 3600,
                    }
                ]
            },
        )


def _ensure_queue() -> None:
    client = _client("sqs")
    queue_name = os.environ["SQS_QUEUE_NAME"]
    response = client.create_queue(QueueName=queue_name)
    queue_url = response.get("QueueUrl")
    if not queue_url:
        raise RuntimeError(f"SQS did not return a URL for queue '{queue_name}'.")
    client.get_queue_attributes(QueueUrl=queue_url, AttributeNames=["QueueArn"])


def main() -> None:
    _load_environment()
    _wait_for_floci()
    _ensure_secret()
    _ensure_bucket()
    _ensure_queue()
    print("Floci initialized with the application secret, S3 bucket, and SQS queue.")


if __name__ == "__main__":
    main()
