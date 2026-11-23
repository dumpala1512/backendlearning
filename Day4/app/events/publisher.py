from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import Any

import boto3

from app.core.config import Settings
from app.schemas.event import EventMessage

logger = logging.getLogger("film_review.events.publisher")


class EventPublisher(ABC):
    """Queue-independent abstraction for publishing domain events."""

    @abstractmethod
    def initialize(self) -> None:
        """Perform any startup validation required by the concrete publisher."""

    @abstractmethod
    def publish(self, event: EventMessage) -> Any:
        """Publish a serialized event to the configured downstream queue."""


class LocalQueuePublisher(EventPublisher):
    """Lightweight in-memory queue used for local development and testability."""

    def __init__(self) -> None:
        self.messages: list[EventMessage] = []

    def initialize(self) -> None:
        return None

    def publish(self, event: EventMessage) -> Any:
        self.messages.append(event)
        logger.info("Published event\n\nEvent Type: %s\n\nResource ID: %s", event.event_type, event.resource_id)
        return event


class QueueEventPublisher(EventPublisher):
    """Amazon SQS-backed publisher."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings
        self.queue_url: str | None = None
        self.enabled = False
        self.client: Any | None = None

    def initialize(self) -> None:
        if self.settings is None:
            raise RuntimeError("SQS publisher requires application settings.")

        self.queue_url = getattr(self.settings, "EVENT_QUEUE_URL", None) or getattr(self.settings, "QUEUE_URL", None)
        if not self.queue_url:
            raise RuntimeError("SQS publisher requires EVENT_QUEUE_URL or QUEUE_URL.")
        if not getattr(self.settings, "EVENT_PUBLISHER_ENABLED", True):
            raise RuntimeError("SQS event publishing is disabled by configuration.")

        client_kwargs: dict[str, Any] = {}
        for setting_name, client_name in (
            ("AWS_REGION", "region_name"),
            ("AWS_ENDPOINT_URL", "endpoint_url"),
            ("AWS_ACCESS_KEY_ID", "aws_access_key_id"),
            ("AWS_SECRET_ACCESS_KEY", "aws_secret_access_key"),
            ("AWS_SESSION_TOKEN", "aws_session_token"),
        ):
            value = getattr(self.settings, setting_name, None)
            if value:
                client_kwargs[client_name] = value

        self.client = boto3.client("sqs", **client_kwargs)
        self.client.get_queue_attributes(QueueUrl=self.queue_url, AttributeNames=["QueueArn"])
        self.enabled = True
        logger.info("Initialized SQS event publisher for queue '%s'.", self.queue_url)

    def publish(self, event: EventMessage) -> Any:
        if not self.enabled or self.client is None or self.queue_url is None:
            raise RuntimeError("SQS event publisher is not initialized.")

        payload = json.dumps(event.model_dump(mode="json", exclude_none=True))
        response = self.client.send_message(QueueUrl=self.queue_url, MessageBody=payload)
        logger.info("Published event\n\nEvent Type: %s\n\nResource ID: %s", event.event_type, event.resource_id)
        return response


def create_event_publisher(settings: Settings | None = None) -> EventPublisher:
    """Create and initialize the configured SQS publisher."""
    if settings is None:
        raise RuntimeError("SQS publisher requires application settings.")
    publisher = QueueEventPublisher(settings)
    publisher.initialize()
    return publisher


__all__ = [
    "EventPublisher",
    "LocalQueuePublisher",
    "QueueEventPublisher",
    "create_event_publisher",
]
