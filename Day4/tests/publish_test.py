from app.core.config import settings
from app.events.publisher import create_event_publisher
from app.schemas.event import EventMessage


def main() -> None:
    print("Creating publisher...")
    publisher = create_event_publisher(settings)

    events = [
        EventMessage.create(
            event_type="review.created",
            resource_id="manual-test-success",
            payload={"test": True},
        ),
        *[
            EventMessage.create(
                event_type="review.created",
                resource_id=f"manual-dlq-test-{index}",
                payload={"test": True, "force_failure": True},
            )
            for index in range(1, 4)
        ],
    ]

    for event in events:
        print(
            f"\nPublishing event: {event.model_dump(mode='json', exclude_none=True)}"
        )

        response = publisher.publish(event)

        print(
            f"Event published successfully. "
            f"SQS message ID: {response.get('MessageId')}"
        )


if __name__ == "__main__":
    main()