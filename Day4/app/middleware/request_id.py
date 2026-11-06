from __future__ import annotations

import logging
import time
import uuid
from contextvars import ContextVar
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

# ContextVar storing request-scoped ID accessible anywhere in the async call stack
request_id_ctx_var: ContextVar[str | None] = ContextVar("request_id", default=None)

logger = logging.getLogger("app.middleware.request_id")


def get_current_request_id() -> str | None:
    """Retrieve the active request ID for the current async task context."""
    return request_id_ctx_var.get()


async def request_id_middleware(request: Request, call_next) -> Response:
    """
    Request ID Middleware:
    - Generates unique request ID (uuid.uuid4()) for every incoming request (or preserves incoming X-Request-ID).
    - Stores request ID on request.state.request_id and context var.
    - Adds X-Request-ID response header.
    - Logs request start and completion with request ID.
    """
    request_id = (
        request.headers.get("X-Request-ID")
        or request.headers.get("x-request-id")
        or str(uuid.uuid4())
    )
    request.state.request_id = request_id
    token = request_id_ctx_var.set(request_id)

    logger.info(
        f"[Request ID: {request_id}] Incoming {request.method} {request.url.path}",
        extra={"request_id": request_id, "path": request.url.path, "method": request.method},
    )

    start_time = time.perf_counter()
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            f"[Request ID: {request_id}] Completed in {duration_ms:.2f} ms",
            extra={"request_id": request_id, "status_code": response.status_code, "duration_ms": duration_ms},
        )
        return response
    finally:
        request_id_ctx_var.reset(token)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware that ensures every HTTP request has a unique request ID.
    Attaches the request ID to ContextVar, request state, and HTTP response headers.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        return await request_id_middleware(request, call_next)
