from __future__ import annotations

import logging
import os
import sys
from app.logging.formatter import JSONFormatter


def configure_logging(log_level: str | int | None = None) -> None:
    """
    Configure global structured JSON logging for the application.
    Resolves log level dynamically from .env / environment settings.
    Replaces existing handlers with a stream handler using JSONFormatter.
    """
    if log_level is None:
        try:
            from app.core.config import settings
            log_level = settings.LOG_LEVEL
        except Exception:
            log_level = os.getenv("LOG_LEVEL", "INFO")

    root_logger = logging.getLogger()

    if isinstance(log_level, str):
        level_int = getattr(logging, log_level.upper(), logging.INFO)
    else:
        level_int = log_level

    root_logger.setLevel(level_int)

    # Remove existing root handlers to prevent duplicate plain text logs
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    # Add stream handler with JSON formatter
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    handler.setLevel(level_int)
    root_logger.addHandler(handler)

    # Align standard uvicorn loggers if present
    for uvicorn_logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        u_logger = logging.getLogger(uvicorn_logger_name)
        u_logger.handlers = [handler]
        u_logger.propagate = False
