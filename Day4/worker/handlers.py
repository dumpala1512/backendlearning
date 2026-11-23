from __future__ import annotations

import logging
import os
from typing import Any

from app.schemas.event import EventMessage

logger = logging.getLogger("film_review.worker.handlers")


class BaseEventHandler:
    """Single-responsibility event handler with idempotency guard."""

    event_type: str

    def __init__(self, processed_event_ids: set[str] | None = None) -> None:
        self.processed_event_ids = processed_event_ids if processed_event_ids is not None else set()

    def _already_processed(self, event: EventMessage) -> bool:
        if event.event_id in self.processed_event_ids:
            logger.info(
                "Skipping duplicate event",
                extra={"event_id": event.event_id, "event_type": event.event_type, "resource_id": event.resource_id},
            )
            return True
        return False

    def _mark_processed(self, event: EventMessage) -> None:
        self.processed_event_ids.add(event.event_id)

    def _simulate_failure_if_requested(self, event: EventMessage) -> None:
        failure_enabled = os.getenv("WORKER_ENABLE_FAILURE_SIMULATION", "").lower() == "true"
        if failure_enabled and event.payload and event.payload.get("force_failure") is True:
            logger.warning(
                "Simulating handler failure for DLQ testing",
                extra={"event_id": event.event_id, "event_type": event.event_type},
            )
            raise RuntimeError("Intentional handler failure for DLQ testing")

    def handle(self, event: EventMessage) -> bool:
        raise NotImplementedError


class ReviewCreatedHandler(BaseEventHandler):
    event_type = "review.created"

    def handle(self, event: EventMessage) -> bool:
        if self._already_processed(event):
            return True
        self._simulate_failure_if_requested(event)
        logger.info(
            "Handling review.created event",
            extra={"event_id": event.event_id, "resource_id": event.resource_id, "review_id": event.review_id},
        )
        self._mark_processed(event)
        logger.info(
            "Processed review.created event successfully",
            extra={"event_id": event.event_id, "resource_id": event.resource_id, "review_id": event.review_id},
        )
        return True


class ReviewUpdatedHandler(BaseEventHandler):
    event_type = "review.updated"

    def handle(self, event: EventMessage) -> bool:
        if self._already_processed(event):
            return True
        self._simulate_failure_if_requested(event)
        logger.info(
            "Handling review.updated event",
            extra={"event_id": event.event_id, "resource_id": event.resource_id, "review_id": event.review_id},
        )
        self._mark_processed(event)
        logger.info(
            "Processed review.updated event successfully",
            extra={"event_id": event.event_id, "resource_id": event.resource_id, "review_id": event.review_id},
        )
        return True


def create_default_handlers(processed_event_ids: set[str] | None = None) -> dict[str, BaseEventHandler]:
    return {
        ReviewCreatedHandler.event_type: ReviewCreatedHandler(processed_event_ids),
        ReviewUpdatedHandler.event_type: ReviewUpdatedHandler(processed_event_ids),
    }
