from __future__ import annotations

import json
import logging
import signal
import threading
from collections.abc import Iterable
from typing import Any

import boto3

from app.core.config import Settings
from app.schemas.event import EventMessage
from worker.handlers import BaseEventHandler, ReviewCreatedHandler, ReviewUpdatedHandler, create_default_handlers

logger = logging.getLogger("film_review.worker.consumer")


class EventDispatcher:
    """Routes a typed event to the correct handler."""

    def __init__(self, handlers: Iterable[BaseEventHandler] | None = None) -> None:
        if handlers is None:
            handlers = [
                ReviewCreatedHandler(),
                ReviewUpdatedHandler(),
            ]
        self.handlers = {handler.event_type: handler for handler in handlers}

    def dispatch(self, event: EventMessage) -> bool:
        handler = self.handlers.get(event.event_type)
        if handler is None:
            logger.warning(
                "Unknown event type detected; discarding message",
                extra={"event_type": event.event_type, "resource_id": event.resource_id, "event_id": event.event_id},
            )
            return False
        logger.info(
            "Dispatching event to handler",
            extra={"event_type": event.event_type, "handler": handler.__class__.__name__, "event_id": event.event_id},
        )
        return handler.handle(event)


class QueueConsumer:
    """Consumes SQS messages, validates payloads, dispatches handlers, and uses DLQ on permanent failure."""

    def __init__(
        self,
        queue_url: str | None = None,
        *,
        settings: Settings | None = None,
        client: Any | None = None,
        dispatcher: EventDispatcher | None = None,
        max_retries: int = 3,
        wait_time_seconds: int = 10,
    ) -> None:
        self.settings = settings or Settings()
        self.queue_url = queue_url or getattr(self.settings, "event_queue_url", None)
        self.max_retries = max_retries
        self.wait_time_seconds = wait_time_seconds
        self.dispatcher = dispatcher or EventDispatcher()
        self.client = client or self._build_client()
        self.dlq_queue_url: str | None = None
        self._stop_event = threading.Event()

    def _build_client(self) -> Any:
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
        logger.info("Connecting to SQS queue", extra={"queue_url": self.queue_url, "region": client_kwargs.get("region_name")})
        client = boto3.client("sqs", **client_kwargs)
        return client

    @property
    def queue_name(self) -> str | None:
        if not self.queue_url:
            return None
        return self.queue_url.rstrip("/").split("/")[-1]

    def ensure_dlq(self) -> str | None:
        if self.queue_url is None:
            logger.warning("Cannot configure DLQ because queue URL is not set")
            return None
        queue_name = self.queue_name
        if queue_name is None:
            return None
        dlq_name = f"{queue_name}-dlq"
        logger.info("Configuring DLQ", extra={"queue_name": queue_name, "dlq_name": dlq_name})
        try:
            response = self.client.create_queue(QueueName=dlq_name)
            self.dlq_queue_url = response.get("QueueUrl")
            if not self.dlq_queue_url:
                raise RuntimeError("DLQ creation did not return a QueueUrl")
            dlq_arn = self.client.get_queue_attributes(
                QueueUrl=self.dlq_queue_url,
                AttributeNames=["QueueArn"],
            ).get("Attributes", {}).get("QueueArn")
            if not dlq_arn:
                raise RuntimeError("DLQ ARN could not be resolved")
            self.client.set_queue_attributes(
                QueueUrl=self.queue_url,
                Attributes={
                    "RedrivePolicy": json.dumps({
                        "deadLetterTargetArn": dlq_arn,
                        "maxReceiveCount": str(self.max_retries),
                    })
                },
            )
            logger.info("DLQ configured successfully", extra={"dlq_queue_url": self.dlq_queue_url, "max_receive_count": self.max_retries})
            return self.dlq_queue_url
        except Exception as exc:  # pragma: no cover - infra-dependent path
            logger.exception("DLQ configuration failed; worker will continue without DLQ", extra={"queue_url": self.queue_url})
            self.dlq_queue_url = None
            return None

    def _receive_message(self) -> dict[str, Any] | None:
        if not self.queue_url:
            logger.warning("No queue URL configured; consumer cannot receive messages")
            return None
        response = self.client.receive_message(
            QueueUrl=self.queue_url,
            AttributeNames=["All"],
            MessageAttributeNames=["All"],
            MaxNumberOfMessages=1,
            WaitTimeSeconds=self.wait_time_seconds,
            VisibilityTimeout=30,
        )
        messages = response.get("Messages") or []
        if not messages:
            return None
        return messages[0]

    def _deserialize_event(self, message: dict[str, Any]) -> EventMessage:
        raw_body = message.get("Body", "")
        body = json.loads(raw_body) if isinstance(raw_body, str) else raw_body
        event = EventMessage.model_validate(body)
        logger.info(
            "Message received",
            extra={"event_type": event.event_type, "event_id": event.event_id, "resource_id": event.resource_id},
        )
        return event

    def _acknowledge(self, message: dict[str, Any]) -> None:
        receipt_handle = message.get("ReceiptHandle")
        if not receipt_handle:
            logger.warning("Cannot acknowledge message without a receipt handle")
            return
        self.client.delete_message(QueueUrl=self.queue_url, ReceiptHandle=receipt_handle)
        logger.info("Message acknowledged", extra={"receipt_handle": receipt_handle})

    def _move_to_dlq(self, message: dict[str, Any], *, error: Exception | None = None) -> None:
        if not self.dlq_queue_url:
            logger.warning("No DLQ configured; message will remain in source queue for redelivery", extra={"message_id": message.get("MessageId")})
            return
        payload = message.get("Body")
        self.client.send_message(QueueUrl=self.dlq_queue_url, MessageBody=payload)
        self.client.delete_message(QueueUrl=self.queue_url, ReceiptHandle=message["ReceiptHandle"])
        logger.warning(
            "Moved message to dead-letter queue",
            extra={
                "message_id": message.get("MessageId"),
                "dlq_queue_url": self.dlq_queue_url,
                "error": str(error) if error else None,
            },
        )

    def _handle_processing_failure(
        self,
        message: dict[str, Any],
        error: Exception,
        event: EventMessage | None = None,
    ) -> None:
        receipt_count = int(message.get("Attributes", {}).get("ApproximateReceiveCount", "1"))
        context = {
            "message_id": message.get("MessageId"),
            "event_type": event.event_type if event else None,
            "event_id": event.event_id if event else None,
            "attempts": receipt_count,
            "max_retries": self.max_retries,
        }
        if receipt_count >= self.max_retries:
            logger.warning("Retry limit reached; moving message to DLQ", extra=context)
            self._move_to_dlq(message, error=error)
        else:
            logger.warning("Retrying message after processing failure", extra=context)

    def process_message(self, message: dict[str, Any]) -> EventMessage | None:
        try:
            event = self._deserialize_event(message)
        except Exception as exc:
            logger.exception(
                "Failed to deserialize message; leaving it unacknowledged for redelivery",
                extra={"message_id": message.get("MessageId")},
            )
            self._handle_processing_failure(message, exc)
            return None

        if not event.event_type:
            logger.warning("Empty event type; discarding invalid message", extra={"message_id": message.get("MessageId")})
            self._acknowledge(message)
            return None

        logger.info("Event type detected", extra={"event_type": event.event_type, "event_id": event.event_id})
        try:
            handled = self.dispatcher.dispatch(event)
            if not handled:
                logger.warning("Unknown event type processed; discarding message", extra={"event_type": event.event_type})
                self._acknowledge(message)
                return event
            self._acknowledge(message)
            logger.info("Successful processing and acknowledgement", extra={"event_type": event.event_type, "event_id": event.event_id})
            return event
        except Exception as exc:
            logger.exception(
                "Failed to process event; message remains unacknowledged for redelivery",
                extra={"event_type": event.event_type, "event_id": event.event_id, "resource_id": event.resource_id},
            )
            self._handle_processing_failure(message, exc, event)
            return None

    def run_forever(self) -> None:
        logger.info("Worker startup complete; waiting for messages")
        try:
            while not self._stop_event.is_set():
                message = self._receive_message()
                if message is None:
                    continue
                try:
                    self.process_message(message)
                except Exception:
                    logger.exception(
                        "Unexpected message processing error; continuing worker loop",
                        extra={"message_id": message.get("MessageId")},
                    )
        except KeyboardInterrupt:
            logger.info("Worker received shutdown signal")
        finally:
            self.shutdown()

    def shutdown(self) -> None:
        self._stop_event.set()
        logger.info("Worker shutdown complete")

    def stop(self) -> None:
        self.shutdown()


def _install_shutdown_handlers(consumer: QueueConsumer) -> None:
    def _handle_signal(signum: int, _frame: Any) -> None:
        logger.info("Received shutdown signal", extra={"signal_number": signum})
        consumer.stop()

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)


__all__ = [
    "EventDispatcher",
    "QueueConsumer",
    "_install_shutdown_handlers",
]
