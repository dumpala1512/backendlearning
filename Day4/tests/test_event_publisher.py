from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.events.publisher import QueueEventPublisher, create_event_publisher
from app.schemas.event import EventMessage


def _settings(**overrides: object) -> SimpleNamespace:
    values: dict[str, object] = {
        "AWS_REGION": "us-east-1",
        "AWS_ENDPOINT_URL": "http://floci:4566",
        "AWS_ACCESS_KEY_ID": "test",
        "AWS_SECRET_ACCESS_KEY": "test",
        "AWS_SESSION_TOKEN": None,
        "EVENT_QUEUE_URL": "http://floci:4566/000000000000/film-review-events",
        "EVENT_PUBLISHER_ENABLED": True,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_publisher_sends_events_to_configured_sqs_queue() -> None:
    mock_client = MagicMock()
    with patch("app.events.publisher.boto3.client", return_value=mock_client) as create_client:
        publisher = create_event_publisher(_settings())
        event = EventMessage.create("review.created", "review-123")
        publisher.publish(event)

    assert isinstance(publisher, QueueEventPublisher)
    create_client.assert_called_once_with(
        "sqs",
        region_name="us-east-1",
        endpoint_url="http://floci:4566",
        aws_access_key_id="test",
        aws_secret_access_key="test",
    )
    mock_client.send_message.assert_called_once()
    request = mock_client.send_message.call_args.kwargs
    assert request["QueueUrl"] == "http://floci:4566/000000000000/film-review-events"
    assert json.loads(request["MessageBody"])["event_type"] == "review.created"


def test_publisher_does_not_fall_back_when_sqs_is_unavailable() -> None:
    mock_client = MagicMock()
    mock_client.get_queue_attributes.side_effect = RuntimeError("SQS unavailable")

    with (
        patch("app.events.publisher.boto3.client", return_value=mock_client),
        pytest.raises(RuntimeError, match="SQS unavailable"),
    ):
        create_event_publisher(_settings())


def test_publisher_does_not_skip_failed_message_delivery() -> None:
    mock_client = MagicMock()
    mock_client.send_message.side_effect = RuntimeError("SendMessage failed")
    with patch("app.events.publisher.boto3.client", return_value=mock_client):
        publisher = create_event_publisher(_settings())
        with pytest.raises(RuntimeError, match="SendMessage failed"):
            publisher.publish(EventMessage.create("review.created", "review-123"))
