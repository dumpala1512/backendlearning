from __future__ import annotations

from typing import TYPE_CHECKING
from fastapi import FastAPI

from app.middleware.request_id import (
    RequestIDMiddleware,
    get_current_request_id,
    request_id_ctx_var,
    request_id_middleware,
)
from app.middleware.response_time import (
    ResponseTimeMiddleware,
    response_time_middleware,
)


def register_middlewares(app: FastAPI) -> None:
    """
    Register all HTTP middlewares on the FastAPI application using @app.middleware('http').
    Order: response_time_middleware is added first (inner),
           request_id_middleware is added second (outer).
    """
    app.middleware("http")(response_time_middleware)
    app.middleware("http")(request_id_middleware)


__all__ = [
    "RequestIDMiddleware",
    "ResponseTimeMiddleware",
    "get_current_request_id",
    "request_id_ctx_var",
    "request_id_middleware",
    "response_time_middleware",
    "register_middlewares",
]
