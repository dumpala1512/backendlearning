from __future__ import annotations

import logging
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


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware that ensures every HTTP request has a unique request ID.
    Attaches the request ID to ContextVar, request state, and HTTP response headers.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Extract existing request ID or generate a new UUID4
        request_id = (
            request.headers.get("X-Request-ID")
            or request.headers.get("x-request-id")
            or str(uuid.uuid4())
        )

        token = request_id_ctx_var.set(request_id)
        request.state.request_id = request_id

        logger.info(
            "HTTP request received: %s %s",
            request.method,
            request.url.path,
            extra={"path": request.url.path, "method": request.method},
        )

        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            request_id_ctx_var.reset(token)
