from __future__ import annotations

import asyncio
from urllib.parse import quote
import logging

from fastapi import APIRouter, Depends, File, Form, Header, Query, Request, UploadFile, status
from fastapi.responses import StreamingResponse

from app.dependencies import get_request_id, get_storage_service
from app.storage.exceptions import StorageValidationError
from app.storage.models import (
    StorageListItem,
    StoragePresignedOperation,
    StoragePresignedUrlResponse,
    StoragePresignedUploadRequest,
    StorageUploadResponse,
)
from app.storage.storage_service import StorageService

logger = logging.getLogger("film_review.routers.storage")

router = APIRouter(prefix="/storage", tags=["Storage"])


@router.post(
    "/upload",
    response_model=StorageUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a file to the configured S3 bucket",
)
async def upload_file(
    file: UploadFile = File(...),
    prefix: str = Form(default="uploads"),
    storage_service: StorageService = Depends(get_storage_service),
    request_id: str = Depends(get_request_id),
) -> StorageUploadResponse:
    logger.info("[%s] Uploading file '%s' to S3 prefix '%s'.", request_id, file.filename, prefix)
    record = await storage_service.upload_file(file=file, prefix=prefix)
    return StorageUploadResponse(
        id=record.id,
        key=record.key,
        filename=record.filename,
        content_type=record.content_type,
        size=record.size,
    )


@router.get(
    "",
    response_model=list[StorageListItem],
    summary="List files under an optional prefix",
)
async def list_files(
    prefix: str = Query(default="", description="Optional S3 key prefix to filter against."),
    storage_service: StorageService = Depends(get_storage_service),
    request_id: str = Depends(get_request_id),
) -> list[StorageListItem]:
    logger.info("[%s] Listing S3 objects under prefix '%s'.", request_id, prefix)
    return await storage_service.list_files(prefix=prefix)


@router.get(
    "/{object_key:path}",
    summary="Download a stored file by its object key",
)
async def get_file(
    object_key: str,
    storage_service: StorageService = Depends(get_storage_service),
    request_id: str = Depends(get_request_id),
    content_disposition: str | None = None,
) -> StreamingResponse:
    logger.info("[%s] Downloading S3 object '%s'.", request_id, object_key)
    object_response = await storage_service.download_file(object_key)
    body = object_response["Body"]
    content_type = object_response.get("ContentType") or "application/octet-stream"
    if content_disposition not in (None, "attachment", "inline"):
        raise StorageValidationError(message="content_disposition must be 'attachment' or 'inline'.")
    filename = object_response.get("Metadata", {}).get("original_filename") or object_key.rsplit("/", 1)[-1]
    disposition = content_disposition or "attachment"
    headers = {"Content-Disposition": f"{disposition}; filename*=UTF-8''{quote(filename, safe='')}"}

    async def stream_file() -> bytes:
        try:
            while True:
                chunk = await asyncio.to_thread(body.read, 65536)
                if not chunk:
                    break
                yield chunk
        finally:
            body.close()

    return StreamingResponse(stream_file(), media_type=content_type, headers=headers)


@router.delete(
    "/{object_key:path}",
    summary="Delete a stored file by object key",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_file(
    object_key: str,
    storage_service: StorageService = Depends(get_storage_service),
    request_id: str = Depends(get_request_id),
) -> None:
    logger.info("[%s] Deleting S3 object '%s'.", request_id, object_key)
    await storage_service.delete_file(object_key)


@router.post(
    "/presign-upload",
    response_model=StoragePresignedUrlResponse,
    summary="Generate a temporary presigned PUT URL for upload",
    description="Returns an upload URL only. The file is stored only after the client sends a PUT to that URL.",
)
async def generate_presigned_upload(
    payload: StoragePresignedUploadRequest,
    storage_service: StorageService = Depends(get_storage_service),
    request_id: str = Depends(get_request_id),
) -> StoragePresignedUrlResponse:
    logger.info("[%s] Generating presigned upload for filename '%s'.", request_id, payload.filename)
    return await storage_service.generate_presigned_upload(
        filename=payload.filename,
        content_type=payload.content_type,
        file_size=payload.file_size,
        prefix=payload.prefix,
    )

@router.post(
    "/presign",
    response_model=StoragePresignedUrlResponse,
    summary="Generate a temporary presigned object URL",
)
async def generate_presigned_url(
    object_key: str,
    expiry: int | None = None,
    operation: StoragePresignedOperation = StoragePresignedOperation.DOWNLOAD,
    content_type: str | None = None,
    file_size: int | None = None,
    content_disposition: str = "attachment",
    storage_service: StorageService = Depends(get_storage_service),
    request_id: str = Depends(get_request_id),
) -> StoragePresignedUrlResponse:
    logger.info("[%s] Generating presigned URL for key '%s'.", request_id, object_key)
    return await storage_service.generate_presigned_url(
        object_key=object_key,
        operation=operation,
        expiry=expiry,
        content_type=content_type,
        file_size=file_size,
        content_disposition=content_disposition,
    )
