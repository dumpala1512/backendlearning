from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from app.middleware.request_id import get_current_request_id


class JSONFormatter(logging.Formatter):
    """
    Structured JSON log formatter.
    Guarantees every log line is valid JSON containing:
    - timestamp (ISO-8601 UTC)
    - level (e.g. INFO, WARNING, ERROR)
    - logger (logger name)
    - message (formatted string)
    - request_id (injected from request context if available)
    """

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.fromtimestamp(record.created, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        log_data: dict[str, Any] = {
            "timestamp": timestamp,
            "level": record.levelname,
            "logger": record.name,
        }

        # Attach request_id if available in request scope
        req_id = getattr(record, "request_id", None) or get_current_request_id()
        if req_id is not None:
            log_data["request_id"] = str(req_id)

        log_data["message"] = record.getMessage()

        # Exception formatting
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Collect any extra contextual fields
        reserved_attrs = {
            "args", "asctime", "created", "exc_info", "exc_text", "filename",
            "funcName", "levelname", "levelno", "lineno", "module", "msecs",
            "msg", "name", "pathname", "process", "processName", "relativeCreated",
            "stack_info", "thread", "threadName", "request_id", "message"
        }
        for key, val in record.__dict__.items():
            if key not in reserved_attrs and not key.startswith("_"):
                try:
                    json.dumps(val)
                    log_data[key] = val
                except (TypeError, OverflowError):
                    log_data[key] = str(val)

        return json.dumps(log_data)
