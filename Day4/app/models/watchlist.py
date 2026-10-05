from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING
import uuid

from sqlalchemy import DateTime, ForeignKey, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.film import Film
    from app.models.user import User


class Watchlist(Base):
    """
    SQLAlchemy 2.0 ORM model for Watchlist table.
    Represents a many-to-many relationship between Users and Films using UUID foreign keys.
    """

    __tablename__ = "watchlist"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    film_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("films.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="watchlist_items")
    film: Mapped[Film] = relationship("Film", back_populates="watchlist_items")

    def __repr__(self) -> str:
        return f"<Watchlist user_id={self.user_id} film_id={self.film_id}>"


WatchlistORM = Watchlist
