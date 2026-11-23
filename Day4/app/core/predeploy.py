"""Platform-specific pre-deployment validation hooks for Film Review Platform."""

import asyncio
import os
import sys
import tempfile

from app.core.config import settings
from app.core.secrets import load_application_credentials
from app.storage.storage_service import StorageService


def check_aws_secrets() -> None:
    """Validate AWS Secrets Manager reachability and required secret keys."""
    secret_name = os.environ.get("AWS_SECRETS_NAME")
    if not secret_name:
        raise ValueError("AWS_SECRETS_NAME is not set")
    region = os.environ.get("AWS_REGION", "us-east-1")
    endpoint = os.environ.get("AWS_ENDPOINT_URL")

    creds = load_application_credentials(secret_name, region_name=region, endpoint_url=endpoint)
    if not creds.get("database_password"):
        raise ValueError("Missing 'database_password' in AWS Secrets Manager payload")
    if not creds.get("token_secret_key"):
        raise ValueError("Missing 'token_secret_key' in AWS Secrets Manager payload")


async def _check_s3_async() -> None:
    service = StorageService(settings)
    await service.verify_bucket_access()

    with tempfile.NamedTemporaryFile(mode="wb", suffix=".txt", delete=False) as handle:
        handle.write(b"pre-deployment-check")
        temp_path = handle.name

    class UploadFileMock:
        def __init__(self, path: str):
            self.filename = "predeployment-check.txt"
            self.content_type = "text/plain"
            self.file = open(path, "rb")

        async def seek(self, offset: int, whence: int = 0) -> int:
            return self.file.seek(offset, whence)

        async def tell(self) -> int:
            return self.file.tell()

    upload = UploadFileMock(temp_path)
    record = await service.upload_file(upload, prefix="healthchecks")
    try:
        assert await service.file_exists(record.key)
        await service.download_file(record.key)
    finally:
        await service.delete_file(record.key)
        if os.path.exists(temp_path):
            os.remove(temp_path)


def check_s3_storage() -> None:
    """Validate S3 bucket read, write, and delete permissions."""
    asyncio.run(_check_s3_async())

