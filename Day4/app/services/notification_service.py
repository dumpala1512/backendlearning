from __future__ import annotations

import logging
from typing import Any
import httpx

logger = logging.getLogger("film_review.services.notification")


class NotificationService:
    """
    Third-party external notification service.
    Sends notifications (email/webhook/SMS) via an external HTTP REST API.
    Used to demonstrate mocking external asynchronous HTTP dependencies and third-party APIs.
    """

    def __init__(
        self,
        api_url: str = "https://api.notifications.example.com",
        api_key: str = "secret-external-api-key",
    ) -> None:
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key

    async def send_review_notification(
        self,
        recipient_email: str,
        film_title: str,
        rating: int,
    ) -> dict[str, Any]:
        """
        Send external notification when a new film review is submitted.
        Must be mocked during tests so no actual network request occurs.
        """
        url = f"{self.api_url}/v1/notifications/review"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "recipient": recipient_email,
            "film_title": film_title,
            "rating": rating,
            "template": "new_review_alert",
        }

        logger.info("Dispatching external notification for film '%s' to %s", film_title, recipient_email)

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json=payload,
                headers=headers,
                timeout=5.0,
            )
            response.raise_for_status()
            data = response.json()

        logger.info("External notification successfully delivered: %s", data)
        return data

    def get_service_status(self) -> dict[str, str]:
        """
        Synchronous method to demonstrate MagicMock for sync third-party calls.
        """
        return {"status": "healthy", "provider": "external-notify-api"}
