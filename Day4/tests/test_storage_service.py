# from __future__ import annotations

# import io
# from unittest.mock import AsyncMock, MagicMock, patch

# import pytest
# from fastapi import FastAPI, UploadFile
# from fastapi.testclient import TestClient

# from app.core.config import Settings
# from app.dependencies import get_storage_service
# from app.exceptions.handlers import register_exception_handlers
# from app.routers.storage import router as storage_router
# from app.storage.exceptions import FileNotFoundError, StorageValidationError
# from app.storage.storage_service import StorageService


# @pytest.fixture
# def mock_settings() -> Settings:
#     return Settings.model_construct(
#         AWS_REGION="us-east-1",
#         AWS_SECRETS_NAME="film-review/credentials",
#         S3_BUCKET_NAME="demo-bucket",
#         S3_ENDPOINT_URL="http://localhost:4566",
#         S3_PRESIGNED_ENDPOINT_URL=None,
#         AWS_ACCESS_KEY_ID="test",
#         AWS_SECRET_ACCESS_KEY="test",
#         S3_SIGNATURE_VERSION="s3v4",
#         PRESIGNED_URL_EXPIRE_SECONDS=120,
#         S3_MAX_FILE_SIZE_BYTES=1024 * 1024,
#         S3_ALLOWED_MIME_TYPES="image/png,text/plain",
#         DB_HOST="localhost",
#         DB_PORT=5432,
#         DB_USER="film_user",
#         DB_NAME="film_review_db",
#         DB_DRIVER="postgresql+asyncpg",
#         REDIS_HOST="localhost",
#         REDIS_PORT=6379,
#         REDIS_DB=0,
#         ACCESS_TOKEN_EXPIRE_MINUTES=30,
#         REFRESH_TOKEN_EXPIRE_DAYS=7,
#         CACHE_TTL_SECONDS=300,
#         LOG_LEVEL="INFO",
#     )


# @pytest.mark.unit
# @pytest.mark.asyncio
# async def test_storage_service_upload_list_download_delete_and_presign(mock_settings: Settings) -> None:
#     mock_client = MagicMock()
#     mock_client.head_bucket.return_value = {}
#     mock_client.put_object.return_value = {"ETag": '"abc123"'}
#     mock_client.list_objects_v2.return_value = {
#         "Contents": [
#             {"Key": "uploads/one.txt", "Size": 12, "LastModified": "2024-01-01", "StorageClass": "STANDARD", "ETag": '"one"'}
#         ]
#     }
#     mock_client.get_object.return_value = {
#         "Body": io.BytesIO(b"hello world"),
#         "ContentType": "text/plain",
#         "ContentDisposition": "attachment; filename=hello.txt",
#     }
#     mock_client.generate_presigned_url.return_value = "https://example.com/hello.txt"

#     with patch("app.storage.storage_service.boto3.client", return_value=mock_client):
#         service = StorageService(mock_settings)
#         file = UploadFile(
#             filename="Screenshot 2026-07-24 125249.png",
#             file=io.BytesIO(b"hello world"),
#             headers={"content-type": "image/png"},
#         )

#         record = await service.upload_file(file=file, prefix="uploads")
#         assert record.id == "uploads/Screenshot 2026-07-24 125249.png"
#         assert record.key == "uploads/Screenshot 2026-07-24 125249.png"
#         assert record.filename == "Screenshot 2026-07-24 125249.png"
#         mock_client.put_object.assert_called_once()
#         assert mock_client.put_object.call_args.kwargs["Key"] == record.key
#         assert mock_client.put_object.call_args.kwargs["ContentDisposition"] == (
#             "attachment; filename*=UTF-8''Screenshot%202026-07-24%20125249.png"
#         )

#         files = await service.list_files(prefix="uploads")
#         assert files[0].key == "uploads/one.txt"

#         downloaded = await service.download_file(record.id)
#         assert downloaded["Body"].read() == b"hello world"

#         presigned = await service.generate_presigned_url(record.id, expiry=60)
#         assert presigned.url == "https://example.com/hello.txt"

#         await service.delete_file(record.id)
#         mock_client.delete_object.assert_called_once_with(Bucket="demo-bucket", Key=record.id)


# @pytest.mark.unit
# @pytest.mark.asyncio
# async def test_presigned_url_uses_browser_reachable_endpoint(mock_settings: Settings) -> None:
#     mock_settings.S3_ENDPOINT_URL = "http://host.docker.internal:4566"
#     mock_settings.S3_PRESIGNED_ENDPOINT_URL = "http://localhost:4566"
#     storage_client = MagicMock()
#     presigned_client = MagicMock()
#     presigned_client.generate_presigned_url.return_value = "http://localhost:4566/demo-bucket/uploads/file.png"

#     with patch(
#         "app.storage.storage_service.boto3.client",
#         side_effect=[storage_client, presigned_client],
#     ) as create_client:
#         service = StorageService(mock_settings)
#         presigned = await service.generate_presigned_url("uploads/file.png", expiry=60)

#     assert create_client.call_count == 2
#     assert create_client.call_args_list[0].kwargs["endpoint_url"] == "http://host.docker.internal:4566"
#     assert create_client.call_args_list[1].kwargs["endpoint_url"] == "http://localhost:4566"
#     presigned_client.generate_presigned_url.assert_called_once_with(
#         "get_object",
#         Params={
#             "Bucket": "demo-bucket",
#             "Key": "uploads/file.png",
#             "ResponseContentDisposition": "attachment; filename*=UTF-8''file.png",
#         },
#         ExpiresIn=60,
#     )
#     storage_client.generate_presigned_url.assert_not_called()
#     assert presigned.url.startswith("http://localhost:4566/")


# @pytest.mark.unit
# def test_download_route_forces_attachment_by_default() -> None:
#     storage_service = MagicMock()
#     storage_service.download_file = AsyncMock(
#         return_value={
#             "Body": io.BytesIO(b"image bytes"),
#             "ContentType": "image/png",
#             "Metadata": {"original_filename": "holiday photo.png"},
#         }
#     )
#     app = FastAPI()
#     app.include_router(storage_router)
#     app.dependency_overrides[get_storage_service] = lambda: storage_service

#     response = TestClient(app).get("/storage/uploads/file-id")

#     assert response.status_code == 200
#     assert response.content == b"image bytes"
#     assert response.headers["content-disposition"] == (
#         "attachment; filename*=UTF-8''holiday%20photo.png"
#     )


# @pytest.mark.unit
# def test_download_route_preserves_filename_when_inline_is_requested() -> None:
#     storage_service = MagicMock()
#     storage_service.download_file = AsyncMock(
#         return_value={
#             "Body": io.BytesIO(b"image bytes"),
#             "ContentType": "image/png",
#             "Metadata": {"original_filename": "holiday photo.png"},
#         }
#     )
#     app = FastAPI()
#     app.include_router(storage_router)
#     app.dependency_overrides[get_storage_service] = lambda: storage_service

#     response = TestClient(app).get("/storage/uploads/file-id?content_disposition=inline")

#     assert response.status_code == 200
#     assert response.headers["content-disposition"] == "inline; filename*=UTF-8''holiday%20photo.png"


# @pytest.mark.unit
# def test_storage_exception_handlers_map_storage_errors() -> None:
#     app = FastAPI()
#     register_exception_handlers(app)

#     @app.get("/missing")
#     async def missing():
#         raise FileNotFoundError(message="No such object")

#     @app.get("/invalid")
#     async def invalid():
#         raise StorageValidationError(message="bad upload")

#     client = TestClient(app)

#     missing_response = client.get("/missing")
#     assert missing_response.status_code == 404
#     assert missing_response.json()["type"] == "FileNotFound"

#     invalid_response = client.get("/invalid")
#     assert invalid_response.status_code == 400
#     assert invalid_response.json()["type"] == "StorageValidation"
