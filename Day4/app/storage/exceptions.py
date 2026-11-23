from __future__ import annotations

from fastapi import status

from app.exceptions.base import DomainError, ValidationError


class StorageError(DomainError):
    """Base class for S3 and file storage infrastructure failures."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_message: str = "A storage operation failed."


class StorageValidationError(ValidationError):
    """Raised when a storage operation receives invalid input or unsupported data."""

    default_message: str = "Storage validation failed."


class FileNotFoundError(StorageError):
    """Raised when an object is missing from the configured S3 bucket."""

    status_code: int = status.HTTP_404_NOT_FOUND
    default_message: str = "The requested file was not found in storage."


class BucketNotFoundError(StorageError):
    """Raised when the configured storage bucket cannot be accessed."""

    status_code: int = status.HTTP_404_NOT_FOUND
    default_message: str = "The configured storage bucket was not found or is inaccessible."


class UploadFailedError(StorageError):
    """Raised when a file upload fails at the storage layer."""

    status_code: int = status.HTTP_502_BAD_GATEWAY
    default_message: str = "The file upload failed." 


class DeleteFailedError(StorageError):
    """Raised when a file deletion fails in storage."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_message: str = "The file deletion failed."


class StoragePermissionDenied(StorageError):
    """Raised when the storage service is not allowed to perform the operation."""

    status_code: int = status.HTTP_403_FORBIDDEN
    default_message: str = "Permission denied for the requested storage operation."


__all__ = [
    "BucketNotFoundError",
    "DeleteFailedError",
    "FileNotFoundError",
    "StorageError",
    "StoragePermissionDenied",
    "StorageValidationError",
    "UploadFailedError",
]
