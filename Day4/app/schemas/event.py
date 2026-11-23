from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator


class EventMessage(BaseModel):
    """Event envelope published to the asynchronous review pipeline.

    The API has historically emitted minimal events carrying ``event_type`` and
    ``resource_id``. The standalone worker adds event-level metadata used for
    idempotency and DLQ handling while keeping backward compatibility with the
    original message format.
    """

    event_type: str
    resource_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    occurred_at: datetime | None = None
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    review_id: str | None = None
    payload: dict[str, Any] | None = None
    version: int = 1

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    @field_validator("timestamp", mode="before")
    @classmethod
    def _ensure_utc(cls, value: Any) -> datetime:
        if value is None:
            return datetime.now(timezone.utc)
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc)
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(timezone.utc)

    @field_validator("occurred_at", mode="before")
    @classmethod
    def _normalize_occurred_at(cls, value: Any) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc)
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(timezone.utc)

    @field_serializer("timestamp")
    def _serialize_timestamp(self, value: datetime, _info: Any) -> str:
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    @field_serializer("occurred_at")
    def _serialize_occurred_at(self, value: datetime | None, _info: Any) -> str | None:
        if value is None:
            return None
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    def model_post_init(self, __context: Any) -> None:
        super().model_post_init(__context)
        if self.occurred_at is None:
            self.occurred_at = self.timestamp
        if self.review_id is None and self.resource_id:
            self.review_id = self.resource_id

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)

    def to_json(self) -> str:
        import json

        return json.dumps(self.to_dict())

    @classmethod
    def create(cls, event_type: str, resource_id: str | int | None, version: int = 1, payload: dict[str, Any] | None = None, event_id: str | None = None) -> "EventMessage":
        return cls(
            event_type=event_type,
            resource_id=str(resource_id),
            version=version,
            payload=payload,
            event_id=event_id or str(uuid.uuid4()),
        )
