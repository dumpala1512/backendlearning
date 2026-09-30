from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.schemas.film import Film
    from app.schemas.user import User


class Review(Base):
    """SQLAlchemy 2.0 ORM model for Reviews table."""

    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    film_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("films.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),     
        index=True,
        nullable=True,
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    review: Mapped[str] = mapped_column(Text, nullable=False)
    reviewer_display_name: Mapped[str] = mapped_column(
        String(50),
        default="Anonymous Critic",           #default value if user is not logged in
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
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
