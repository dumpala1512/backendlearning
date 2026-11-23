from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from app.schemas.event import EventMessage
from worker.consumer import EventDispatcher, QueueConsumer
from worker.handlers import BaseEventHandler, ReviewCreatedHandler


class FailingReviewCreatedHandler(BaseEventHandler):
    event_type = "review.created"

    def handle(self, event: EventMessage) -> bool:
        raise RuntimeError("Testing DLQ")


def test_event_message_supports_worker_metadata() -> None:
    event = EventMessage.create("review.created", "review-123", payload={"status": "published"})

    assert event.event_id
    assert event.review_id == "review-123"
    assert event.payload == {"status": "published"}


def test_event_dispatcher_routes_known_events() -> None:
    dispatcher = EventDispatcher()

    created = EventMessage.create("review.created", "review-123")
    updated = EventMessage.create("review.updated", "review-456")
    unknown = EventMessage.create("review.deleted", "review-789")

    assert dispatcher.dispatch(created) is True
    assert dispatcher.dispatch(updated) is True
    assert dispatcher.dispatch(unknown) is False


def test_failure_simulation_is_opt_in(monkeypatch: pytest.MonkeyPatch) -> None:
    event = EventMessage.create(
        "review.created",
        "review-failure-test",
        payload={"force_failure": True},
    )
    handler = ReviewCreatedHandler()

    monkeypatch.delenv("WORKER_ENABLE_FAILURE_SIMULATION", raising=False)
    assert handler.handle(event) is True

    monkeypatch.setenv("WORKER_ENABLE_FAILURE_SIMULATION", "true")
    with pytest.raises(RuntimeError, match="Intentional handler failure"):
        handler.handle(EventMessage.create(
            "review.created",
            "review-failure-test",
            payload={"force_failure": True},
        ))


def test_consumer_moves_failed_message_to_dlq_after_retry_limit() -> None:
    queue_url = "http://localhost:4566/000000000000/film-review-queue"
    dlq_url = "http://localhost:4566/000000000000/film-review-queue-dlq"
    client = MagicMock()
    client.receive_message.return_value = {
        "Messages": [
            {
                "MessageId": "msg-1",
                "ReceiptHandle": "handle-1",
                "Body": json.dumps({
                    "event_type": "review.created",
                    "resource_id": "review-123",
                    "event_id": "event-1",
                    "timestamp": "2026-01-01T00:00:00Z",
                }),
                "Attributes": {"ApproximateReceiveCount": "3"},
            }
        ]
    }
    dispatcher = EventDispatcher([FailingReviewCreatedHandler()])
    consumer = QueueConsumer(queue_url=queue_url, client=client, dispatcher=dispatcher, max_retries=3)
    consumer.dlq_queue_url = dlq_url

    event = consumer.process_message(client.receive_message.return_value["Messages"][0])

    assert event is None
    client.send_message.assert_called_once_with(QueueUrl=dlq_url, MessageBody=client.receive_message.return_value["Messages"][0]["Body"])
    client.delete_message.assert_called_once_with(QueueUrl=queue_url, ReceiptHandle="handle-1")


def test_consumer_retries_malformed_message_without_stopping() -> None:
    client = MagicMock()
    consumer = QueueConsumer(
        queue_url="http://localhost:4566/000000000000/film-review-queue",
        client=client,
        max_retries=3,
    )
    message = {
        "MessageId": "invalid-json",
        "ReceiptHandle": "handle-invalid",
        "Body": "not-json",
        "Attributes": {"ApproximateReceiveCount": "1"},
    }

    assert consumer.process_message(message) is None
    client.delete_message.assert_not_called()
    client.send_message.assert_not_called()


def test_consumer_moves_malformed_message_to_dlq_after_retry_limit() -> None:
    queue_url = "http://localhost:4566/000000000000/film-review-queue"
    dlq_url = "http://localhost:4566/000000000000/film-review-queue-dlq"
    client = MagicMock()
    consumer = QueueConsumer(queue_url=queue_url, client=client, max_retries=3)
    consumer.dlq_queue_url = dlq_url
    message = {
        "MessageId": "invalid-json",
        "ReceiptHandle": "handle-invalid",
        "Body": "not-json",
        "Attributes": {"ApproximateReceiveCount": "3"},
    }

    assert consumer.process_message(message) is None
    client.send_message.assert_called_once_with(QueueUrl=dlq_url, MessageBody="not-json")
    client.delete_message.assert_called_once_with(QueueUrl=queue_url, ReceiptHandle="handle-invalid")
