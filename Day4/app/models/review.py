from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING
import uuid

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.film import Film
    from app.models.user import User


class Review(Base):
    """SQLAlchemy 2.0 ORM model for Reviews table."""

    __tablename__ = "reviews"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    film_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("films.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    review: Mapped[str] = mapped_column(Text, nullable=False)
    reviewer_display_name: Mapped[str] = mapped_column(
        String(50),
        default="Anonymous Critic",
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    # Relationship: A Review belongs to one Film
    film: Mapped[Film] = relationship("Film", back_populates="reviews")

    # Relationship: A Review belongs to one User
    user: Mapped[User | None] = relationship("User", back_populates="reviews")

    @property
    def submitted_at(self) -> datetime:
        """Alias for compatibility with ReviewResponse schema."""
        return self.created_at

    def __repr__(self) -> str:
        return f"<Review id={self.id} film_id={self.film_id} rating={self.rating}>"


ReviewORM = Review
