from __future__ import annotations

import io
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, UploadFile
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.dependencies import get_storage_service
from app.storage.models import StoragePresignedOperation
from app.storage.models import StoragePresignedUrlResponse
from app.routers.storage import router as storage_router
from app.storage.storage_service import StorageService


@pytest.fixture
def storage_settings() -> Settings:
    with patch(
        "app.core.config.load_application_credentials",
        side_effect=RuntimeError("Secrets are not needed in this unit test."),
    ):
        return Settings.model_construct(
            AWS_REGION="us-east-1",
            AWS_SECRETS_NAME="test-secret",
            AWS_ACCESS_KEY_ID="test",
            AWS_SECRET_ACCESS_KEY="test",
            AWS_SESSION_TOKEN=None,
            AWS_ENDPOINT_URL=None,
            S3_ENDPOINT_URL=None,
            S3_PRESIGNED_ENDPOINT_URL=None,
            S3_BUCKET_NAME="demo-bucket",
            S3_SIGNATURE_VERSION="s3v4",
            PRESIGNED_URL_EXPIRE_SECONDS=120,
            S3_MAX_FILE_SIZE_BYTES=1024 * 1024,
            S3_ALLOWED_MIME_TYPES="image/png,text/plain",
            POSTGRES_PASSWORD="test",
            LOCAL_TOKEN_SECRET_KEY="test",
            DB_DRIVER="postgresql+asyncpg",
            DB_USER="film_user",
            DB_HOST="localhost",
            DB_PORT=5432,
            DB_NAME="film_review",
        )


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("operation", "expected_params"),
    [
        (
            StoragePresignedOperation.DOWNLOAD,
            {
                "Bucket": "demo-bucket",
                "Key": "uploads/file.png",
                "ResponseContentDisposition": "attachment; filename*=UTF-8''file.png",
            },
        ),
        (
            StoragePresignedOperation.UPLOAD,
            {
                "Bucket": "demo-bucket",
                "Key": "uploads/file.png",
                "ContentType": "image/png",
                "ContentDisposition": "inline; filename*=UTF-8''file.png",
            },
        ),
    ],
)
async def test_presigned_url_uses_requested_operation(
    storage_settings: Settings,
    operation: StoragePresignedOperation,
    expected_params: dict[str, str | int],
) -> None:
    mock_client = MagicMock()
    mock_client.generate_presigned_url.return_value = "https://example.test/signed"

    with patch("app.storage.storage_service.boto3.client", return_value=mock_client):
        service = StorageService(storage_settings)
        result = await service.generate_presigned_url(
            object_key="uploads/file.png",
            operation=operation,
            content_type="image/png" if operation is StoragePresignedOperation.UPLOAD else None,
            file_size=128 if operation is StoragePresignedOperation.UPLOAD else None,
        )

    mock_client.generate_presigned_url.assert_called_once_with(
        operation.value,
        Params=expected_params,
        ExpiresIn=120,
    )
    assert result.url == "https://example.test/signed"
    assert result.object_key == "uploads/file.png"
    assert result.http_method == ("PUT" if operation is StoragePresignedOperation.UPLOAD else "GET")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_presigned_upload_validates_and_returns_required_headers(storage_settings: Settings) -> None:
    mock_client = MagicMock()
    mock_client.generate_presigned_url.return_value = "https://example.test/signed"

    with patch("app.storage.storage_service.boto3.client", return_value=mock_client):
        service = StorageService(storage_settings)
        result = await service.generate_presigned_upload(
            filename="poster.png",
            content_type="image/png",
            file_size=128,
        )

    assert result.object_key == "uploads/poster.png"
    assert result.http_method == "PUT"
    assert result.headers == {
        "Content-Type": "image/png",
        "Content-Disposition": "inline; filename*=UTF-8''poster.png",
    }


@pytest.mark.unit
@pytest.mark.asyncio
async def test_server_upload_stores_inline_content_disposition(storage_settings: Settings) -> None:
    mock_client = MagicMock()

    with patch("app.storage.storage_service.boto3.client", return_value=mock_client):
        service = StorageService(storage_settings)
        await service.upload_file(
            UploadFile(
                filename="poster.png",
                file=io.BytesIO(b"png"),
                headers={"content-type": "image/png"},
            )
        )

    assert mock_client.put_object.call_args.kwargs["ContentDisposition"] == (
        "inline; filename*=UTF-8''poster.png"
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_presigned_download_can_render_inline(storage_settings: Settings) -> None:
    mock_client = MagicMock()
    mock_client.generate_presigned_url.return_value = "https://example.test/signed"

    with patch("app.storage.storage_service.boto3.client", return_value=mock_client):
        service = StorageService(storage_settings)
        await service.generate_presigned_url(
            object_key="new/photo",
            operation=StoragePresignedOperation.DOWNLOAD,
            content_disposition="inline",
        )

    mock_client.generate_presigned_url.assert_called_once_with(
        StoragePresignedOperation.DOWNLOAD.value,
        Params={
            "Bucket": "demo-bucket",
            "Key": "new/photo",
            "ResponseContentDisposition": "inline; filename*=UTF-8''photo",
        },
        ExpiresIn=120,
    )


@pytest.mark.unit
def test_presign_route_passes_requested_operation() -> None:
    storage_service = MagicMock()
    storage_service.generate_presigned_url = AsyncMock(
        return_value=StoragePresignedUrlResponse(
            object_key="uploads/file.png",
            url="https://example.test/signed",
            http_method="GET",
            expires_in=120,
        )
    )
    app = FastAPI()
    app.include_router(storage_router)
    app.dependency_overrides[get_storage_service] = lambda: storage_service

    response = TestClient(app).post(
        "/storage/presign",
        params={
            "object_key": "uploads/file.png",
            "operation": StoragePresignedOperation.UPLOAD.value,
            "content_type": "image/png",
            "file_size": 128,
        },
    )

    assert response.status_code == 200
    storage_service.generate_presigned_url.assert_awaited_once_with(
        object_key="uploads/file.png",
        operation=StoragePresignedOperation.UPLOAD,
        expiry=None,
        content_type="image/png",
        file_size=128,
        content_disposition="attachment",
    )
