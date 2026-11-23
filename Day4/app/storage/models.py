from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class StorageFileRecord(BaseModel):
    """Stable file metadata persisted by the storage service."""

    id: str
    key: str
    filename: str
    content_type: str | None = None
    size: int = 0
    last_modified: datetime | None = None
    e_tag: str | None = Field(default=None, alias="etag")
    storage_class: str | None = None

    model_config = {"populate_by_name": True}


class StorageUploadResponse(BaseModel):
    id: str
    key: str
    filename: str
    content_type: str | None = None
    size: int = 0


class StorageListItem(BaseModel):
    key: str
    size: int = 0
    last_modified: datetime | None = None
    storage_class: str | None = None
    etag: str | None = None


class StoragePresignedOperation(str, Enum):
    DOWNLOAD = "get_object"
    UPLOAD = "put_object"


class StoragePresignedUrlResponse(BaseModel):
    object_key: str
    url: str
    http_method: str
    expires_in: int
    headers: dict[str, str] = Field(default_factory=dict)


class StoragePresignedUploadRequest(BaseModel):
    filename: str = Field(..., min_length=1, max_length=255)
    content_type: str = Field(..., min_length=1, max_length=255)
    file_size: int = Field(..., gt=0)
    prefix: str = Field(default="uploads", max_length=200)


__all__ = [
    "StorageFileRecord",
    "StorageListItem",
    "StoragePresignedOperation",
    "StoragePresignedUrlResponse",
    "StoragePresignedUploadRequest",
    "StorageUploadResponse",
]
