from datetime import datetime
from pydantic import BaseModel, Field


class UserRegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, examples=["moviebuff"])
    email: str = Field(..., examples=["moviebuff@example.com"])
    password: str = Field(..., min_length=6, examples=["secret123"])


class UserLoginRequest(BaseModel):
    username: str = Field(..., examples=["moviebuff"])
    password: str = Field(..., examples=["secret123"])


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    is_admin: bool
    created_at: datetime


class AdminStatsResponse(BaseModel):
    total_users: int
    total_films: int
    total_reviews: int
    uptime_status: str = "healthy"
