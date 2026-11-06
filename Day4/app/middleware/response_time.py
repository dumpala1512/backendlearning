from __future__ import annotations

import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint


async def response_time_middleware(request: Request, call_next) -> Response:
    """
    Response Time Middleware:
    Measures the total processing time for every request using time.perf_counter().
    Adds X-Process-Time response header (e.g. 18.42ms).
    """
    start_time = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start_time) * 1000
    response.headers["X-Process-Time"] = f"{elapsed_ms:.2f}ms"
    return response


class ResponseTimeMiddleware(BaseHTTPMiddleware):
    """
    Middleware measuring request execution duration.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        return await response_time_middleware(request, call_next)
