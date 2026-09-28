from app.schemas.common import HealthResponse, MessageResponse
from app.schemas.film import FilmCreate, FilmResponse, FilmUpdate
from app.schemas.review import ReviewCreate, ReviewResponse, ReviewUpdate
from app.schemas.user import (
    AdminStatsResponse,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)

__all__ = [
    "HealthResponse",
    "MessageResponse",
    "FilmCreate",
    "FilmUpdate",
    "FilmResponse",
    "ReviewCreate",
    "ReviewUpdate",
    "ReviewResponse",
    "UserRegisterRequest",
    "UserLoginRequest",
    "TokenResponse",
    "UserResponse",
    "AdminStatsResponse",
]
