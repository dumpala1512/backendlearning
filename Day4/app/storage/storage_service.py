from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any
from urllib.parse import quote

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, NoCredentialsError
from fastapi import UploadFile

from app.core.config import Settings
from app.storage.exceptions import (
    BucketNotFoundError,
    DeleteFailedError,
    FileNotFoundError,
    StorageError,
    StoragePermissionDenied,
    StorageValidationError,
    UploadFailedError,
)
from app.storage.models import (
    StorageFileRecord,
    StorageListItem,
    StoragePresignedOperation,
    StoragePresignedUrlResponse,
)


class StorageService:
    """Dedicated S3 storage layer that isolates boto3 usage behind a single service abstraction."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.logger = logging.getLogger("film_review.storage")
        self.bucket_name = settings.S3_BUCKET_NAME
        self.client = self._build_client()
        presigned_endpoint_url = settings.S3_PRESIGNED_ENDPOINT_URL
        if presigned_endpoint_url and presigned_endpoint_url != settings.s3_endpoint_url:
            self.presigned_client = self._build_client(endpoint_url=presigned_endpoint_url)
        else:
            self.presigned_client = self.client

    def _build_client(self, endpoint_url: str | None = None) -> Any:
        """Construct a boto3 S3 client configured from app settings."""
        client_kwargs: dict[str, Any] = {
            "region_name": self.settings.AWS_REGION,
            "aws_access_key_id": self.settings.AWS_ACCESS_KEY_ID,
            "aws_secret_access_key": self.settings.AWS_SECRET_ACCESS_KEY,
            "config": Config(
                signature_version=self.settings.S3_SIGNATURE_VERSION or "s3v4",
                s3={"addressing_style": "path"},
            ),
        }
        endpoint_url = endpoint_url or self.settings.s3_endpoint_url
        if endpoint_url:
            client_kwargs["endpoint_url"] = endpoint_url
        if self.settings.AWS_SESSION_TOKEN:
            client_kwargs["aws_session_token"] = self.settings.AWS_SESSION_TOKEN
        return boto3.client("s3", **client_kwargs)

    @property
    def s3_client(self) -> Any:
        return self.client

    def _prefix_value(self, prefix: str | None) -> str:
        if prefix is None:
            return "uploads"
        cleaned = prefix.strip().strip("/")
        return cleaned or "uploads"

    def _object_key_for(self, filename: str, prefix: str = "uploads") -> str:
        if not filename or not filename.strip():
            raise StorageValidationError(message="A filename is required for uploads.")

        safe_name = Path(filename).name
        if not safe_name:
            raise StorageValidationError(message="A valid filename is required for uploads.")

        normalized_prefix = self._prefix_value(prefix)
        return f"{normalized_prefix}/{safe_name}"

    def _attachment_disposition(self, filename: str) -> str:
        safe_filename = Path(filename).name
        return f"attachment; filename*=UTF-8''{quote(safe_filename, safe='')}"

    def _inline_disposition(self, filename: str) -> str:
        safe_filename = Path(filename).name
        return f"inline; filename*=UTF-8''{quote(safe_filename, safe='')}" 

    def _validate_allowed_content_type(self, content_type: str | None) -> None:
        allowed_types = self.settings.S3_ALLOWED_MIME_TYPES
        if not allowed_types:
            return
        allowed = {item.strip().lower() for item in allowed_types.split(",") if item.strip()}
        if not content_type:
            raise StorageValidationError(message="Missing content type for upload validation.")
        if content_type.lower() not in allowed:
            raise StorageValidationError(
                message=f"Unsupported content type '{content_type}'. Allowed types: {', '.join(sorted(allowed))}."
            )

    def _validate_file_size(self, size_bytes: int | None) -> None:
        if size_bytes is None:
            return
        max_size = self.settings.S3_MAX_FILE_SIZE_BYTES
        if max_size is None:
            return
        if size_bytes > max_size:
            raise StorageValidationError(
                message=f"File is too large: {size_bytes} bytes exceeds the maximum allowed size of {max_size} bytes."
            )

    async def verify_bucket_access(self) -> None:
        """Validate bucket existence and access at startup time before serving requests."""
        try:
            await asyncio.to_thread(self.client.head_bucket, Bucket=self.bucket_name)
            self.logger.info("Verified S3 bucket '%s' is accessible.", self.bucket_name)
        except ClientError as exc:
            self.logger.exception("S3 bucket verification failed for bucket '%s'.", self.bucket_name)
            raise self._map_client_error(exc, operation="verify_bucket")
        except NoCredentialsError as exc:
            raise StoragePermissionDenied(message="No valid AWS credentials were provided for S3 access.") from exc

    async def upload_file(self, file: UploadFile, prefix: str = "uploads", metadata: dict[str, str] | None = None) -> StorageFileRecord:
        if file is None or not file.filename:
            raise StorageValidationError(message="Upload requires a valid file with a filename.")

        file.file.seek(0, 2)
        size_bytes = file.file.tell()
        file.file.seek(0)

        if size_bytes <= 0:
            raise StorageValidationError(message="Cannot upload an empty file.")

        self._validate_file_size(size_bytes)
        self._validate_allowed_content_type(file.content_type)

        object_key = self._object_key_for(file.filename, prefix=prefix)
        object_metadata = {"original_filename": file.filename}
        if metadata:
            object_metadata.update(metadata)

        try:
            await asyncio.to_thread(
                self.client.put_object,
                Bucket=self.bucket_name,
                Key=object_key,
                Body=file.file,
                ContentType=file.content_type or "application/octet-stream",
                ContentDisposition=self._inline_disposition(file.filename),
                Metadata=object_metadata,
            )
        except ClientError as exc:
            raise self._map_client_error(exc, operation="upload") from exc
        except Exception as exc:  # pragma: no cover - defensive guard
            raise UploadFailedError(message=f"Upload failed for '{file.filename}'.") from exc

        self.logger.info("Uploaded file to S3 bucket '%s' with key '%s'.", self.bucket_name, object_key)
        return StorageFileRecord(
            id=object_key,
            key=object_key,
            filename=file.filename,
            content_type=file.content_type,
            size=size_bytes,
        )

    async def download_file(self, object_key: str) -> dict[str, Any]:
        normalized_key = self._normalize_object_key(object_key)
        try:
            response = await asyncio.to_thread(self.client.get_object, Bucket=self.bucket_name, Key=normalized_key)
        except ClientError as exc:
            raise self._map_client_error(exc, operation="download") from exc
        self.logger.info("Downloaded file '%s' from S3 bucket '%s'.", normalized_key, self.bucket_name)
        return response

    async def delete_file(self, object_key: str) -> None:
        normalized_key = self._normalize_object_key(object_key)
        try:
            await asyncio.to_thread(self.client.delete_object, Bucket=self.bucket_name, Key=normalized_key)
        except ClientError as exc:
            raise self._map_client_error(exc, operation="delete") from exc
        self.logger.info("Deleted file '%s' from S3 bucket '%s'.", normalized_key, self.bucket_name)

    async def list_files(self, prefix: str = "") -> list[StorageListItem]:
        normalized_prefix = self._prefix_value(prefix) if prefix else ""
        try:
            response = await asyncio.to_thread(self.client.list_objects_v2, Bucket=self.bucket_name, Prefix=normalized_prefix)
        except ClientError as exc:
            raise self._map_client_error(exc, operation="list") from exc

        contents = response.get("Contents", [])
        return [
            StorageListItem(
                key=item.get("Key", ""),
                size=int(item.get("Size", 0) or 0),
                last_modified=item.get("LastModified"),
                storage_class=item.get("StorageClass"),
                etag=item.get("ETag", "").strip('"'),
            )
            for item in contents
        ]

    async def generate_presigned_url(
        self,
        object_key: str,
        operation: StoragePresignedOperation = StoragePresignedOperation.DOWNLOAD,
        expiry: int | None = None,
        content_type: str | None = None,
        file_size: int | None = None,
        content_disposition: str = "attachment",
    ) -> StoragePresignedUrlResponse:
        normalized_key = self._normalize_object_key(object_key)
        expires_in = expiry if expiry is not None else int(self.settings.PRESIGNED_URL_EXPIRE_SECONDS)
        filename = normalized_key.rsplit("/", 1)[-1]
        params: dict[str, Any] = {"Bucket": self.bucket_name, "Key": normalized_key}
        required_headers: dict[str, str] = {}

        if operation is StoragePresignedOperation.UPLOAD:
            if not content_type:
                raise StorageValidationError(message="Missing content type for upload validation.")
            if file_size is None or file_size <= 0:
                raise StorageValidationError(message="A positive file size is required for uploads.")
            self._validate_file_size(file_size)
            self._validate_allowed_content_type(content_type)
            content_disposition = self._inline_disposition(filename)
            params.update(
                {
                    "ContentType": content_type,
                    "ContentDisposition": content_disposition,
                }
            )
            required_headers = {
                "Content-Type": content_type,
                "Content-Disposition": content_disposition,
            }
        else:
            if content_disposition not in {"attachment", "inline"}:
                raise StorageValidationError(
                    message="content_disposition must be 'attachment' or 'inline'."
                )
            disposition = (
                self._attachment_disposition(filename)
                if content_disposition == "attachment"
                else self._inline_disposition(filename)
            )
            params["ResponseContentDisposition"] = disposition

        try:
            url = await asyncio.to_thread(
                self.presigned_client.generate_presigned_url,
                operation.value,
                Params=params,
                ExpiresIn=expires_in,
            )
        except ClientError as exc:
            raise self._map_client_error(exc, operation="presign") from exc
        self.logger.info("Generated presigned URL for object '%s' with expiry %s seconds.", normalized_key, expires_in)
        return StoragePresignedUrlResponse(
            object_key=normalized_key,
            url=url,
            http_method="PUT" if operation is StoragePresignedOperation.UPLOAD else "GET",
            expires_in=expires_in,
            headers=required_headers,
        )

    async def generate_presigned_upload(
        self,
        filename: str,
        content_type: str,
        file_size: int,
        prefix: str = "uploads",
        expiry: int | None = None,
    ) -> StoragePresignedUrlResponse:
        if not filename or not filename.strip():
            raise StorageValidationError(message="A filename is required for uploads.")
        object_key = self._object_key_for(filename, prefix=prefix)
        return await self.generate_presigned_url(
            object_key=object_key,
            operation=StoragePresignedOperation.UPLOAD,
            expiry=expiry,
            content_type=content_type,
            file_size=file_size,
        )

    async def file_exists(self, object_key: str) -> bool:
        normalized_key = self._normalize_object_key(object_key)
        try:
            await asyncio.to_thread(self.client.head_object, Bucket=self.bucket_name, Key=normalized_key)
            return True
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code")
            if error_code in {"404", "NoSuchKey", "NotFound"}:
                return False
            raise self._map_client_error(exc, operation="exists") from exc

    def _normalize_object_key(self, object_key: str) -> str:
        normalized = (object_key or "").strip()
        if not normalized:
            raise StorageValidationError(message="Object key cannot be empty.")
        if normalized.startswith("/"):
            normalized = normalized.lstrip("/")
        if not normalized:
            raise StorageValidationError(message="Object key cannot be empty.")
        return normalized

    def _map_client_error(self, exc: ClientError, operation: str) -> StorageError:
        error = exc.response.get("Error", {})
        code = str(error.get("Code") or "ClientError")
        message = str(error.get("Message") or str(exc))

        if code in {"NoSuchKey", "NotFound", "404"}:
            return FileNotFoundError(message=f"File not found while {operation}: {message}")
        if code in {"NoSuchBucket", "BucketNotFound"}:
            return BucketNotFoundError(message=f"Storage bucket '{self.bucket_name}' was not found while {operation}.")
        if code in {"AccessDenied", "403", "Forbidden"}:
            return StoragePermissionDenied(message=f"Access denied while {operation}: {message}")
        if code == "InvalidObjectState":
            return StorageError(message=f"The file object has an invalid state while {operation}: {message}")
        if code in {"InvalidAccessKeyId", "SignatureDoesNotMatch"}:
            return StoragePermissionDenied(message="S3 credentials are invalid or expired.")
        return UploadFailedError(message=f"S3 request failed while {operation}: {message}") if operation == "upload" else StorageError(message=f"S3 request failed while {operation}: {message}")

    async def close(self) -> None:
        """Close the underlying boto3 client gracefully."""
        clients = (self.client, self.presigned_client)
        for index, client in enumerate(clients):
            if index == 1 and client is self.client:
                continue
            if hasattr(client, "close"):
                client.close()
