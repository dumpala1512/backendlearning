from app.schemas.base import AppBaseModel
from app.schemas.common import HealthResponse, MessageResponse
from app.schemas.film import (
    Film,
    FilmBase,
    FilmCreate,
    FilmFilterQuery,
    FilmResponse,
    FilmUpdate,
)
from app.schemas.review import (
    RatingRangeFilter,
    Review,
    ReviewBase,
    ReviewCreate,
    ReviewResponse,
    ReviewUpdate,
)
from app.schemas.user import (
    AdminStatsResponse,
    TokenResponse,
    User,
    UserBase,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
# Re-export ORM models for services and DAOs that import from app.schemas
from app.models.film import Film as FilmORM
from app.models.review import Review as ReviewORM
from app.models.user import User as UserORM
from app.models.watchlist import Watchlist as WatchlistORM

__all__ = [
    "AppBaseModel",
    "HealthResponse",
    "MessageResponse",
    "Film",
    "FilmBase",
    "FilmCreate",
    "FilmUpdate",
    "FilmResponse",
    "FilmFilterQuery",
    "Review",
    "ReviewBase",
    "ReviewCreate",
    "ReviewUpdate",
    "ReviewResponse",
    "RatingRangeFilter",
    "User",
    "UserBase",
    "UserRegisterRequest",
    "UserLoginRequest",
    "UserResponse",
    "TokenResponse",
    "AdminStatsResponse",
    "FilmORM",
    "ReviewORM",
    "UserORM",
    "WatchlistORM",
]
