from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.schemas.review import Review


class Film(Base):
    """SQLAlchemy 2.0 ORM model for Films table."""

    __tablename__ = "films"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), index=True, nullable=False)
    director: Mapped[str] = mapped_column(String(100), nullable=False)
    release_year: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    genre: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationship: A Film has many Reviews
    reviews: Mapped[list[Review]] = relationship(
        "Review",
        back_populates="film",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Film id={self.id} title='{self.title}' release_year={self.release_year}>"


FilmORM = Film
