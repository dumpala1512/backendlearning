from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING
import uuid

from sqlalchemy import DateTime, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.review import Review
    from app.models.watchlist import Watchlist


class User(Base):
    """SQLAlchemy 2.0 ORM model for Users table."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="user", nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    # Relationship: A User has many Reviews
    reviews: Mapped[list[Review]] = relationship(
        "Review",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    # Relationship: A User can have many Films in their Watchlist
    watchlist_items: Mapped[list[Watchlist]] = relationship(
        "Watchlist",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} username='{self.username}'>"

    @property
    def fullname(self) -> str:
        return self.full_name

    @fullname.setter
    def fullname(self, value: str) -> None:
        self.full_name = value


UserORM = User
