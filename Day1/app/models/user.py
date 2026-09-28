from datetime import datetime, timezone
from pydantic import BaseModel, Field


class User(BaseModel):
    id: int
    username: str
    email: str
    hashed_password: str
    is_admin: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
