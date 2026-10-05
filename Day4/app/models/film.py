from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING
import uuid

from sqlalchemy import Boolean, DateTime, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.review import Review
    from app.models.watchlist import Watchlist


class Film(Base):
    """SQLAlchemy 2.0 ORM model for Films table."""

    __tablename__ = "films"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    title: Mapped[str] = mapped_column(String(200), index=True, nullable=False)
    director: Mapped[str] = mapped_column(String(100), nullable=False)
    release_year: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    genre: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    # Relationship: A Film has many Reviews
    reviews: Mapped[list[Review]] = relationship(
        "Review",
        back_populates="film",
        cascade="all, delete-orphan",
    )

    # Relationship: A Film can be in many Users' Watchlists
    watchlist_items: Mapped[list[Watchlist]] = relationship(
        "Watchlist",
        back_populates="film",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Film id={self.id} title='{self.title}' release_year={self.release_year}>"


FilmORM = Film
