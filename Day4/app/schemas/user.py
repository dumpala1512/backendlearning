from datetime import datetime, timezone
import uuid
from pydantic import EmailStr, Field, SecretStr, field_validator, model_validator
from app.schemas.base import AppBaseModel


class UserBase(AppBaseModel):
    """Reusable user base model exposing username, full_name, email, and role."""

    username: str = Field(..., min_length=3, max_length=50)
    full_name: str = Field(default="", max_length=100)
    email: EmailStr
    role: str = Field(default="user")

    @model_validator(mode="before")
    @classmethod
    def handle_fullname_alias(cls, data: object) -> object:
        if isinstance(data, dict):
            if "fullname" in data and not data.get("full_name"):
                data["full_name"] = data["fullname"]
        return data

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        allowed = {"user", "critic", "moderator", "admin"}
        normalized = v.strip().lower()
        if normalized not in allowed:
            raise ValueError(f"Role must be one of: {', '.join(sorted(allowed))}")
        return normalized


class UserRegisterRequest(UserBase):
    """Registration model with password protected by SecretStr."""

    password: SecretStr = Field(..., min_length=6)
    confirm_password: SecretStr | None = None

    @model_validator(mode="after")
    def validate_passwords(self) -> "UserRegisterRequest":
        pwd = self.password.get_secret_value()
        if self.confirm_password and pwd != self.confirm_password.get_secret_value():
            raise ValueError("Passwords do not match")
        if self.username.lower() in pwd.lower():
            raise ValueError("Password cannot contain the username")
        return self


class UserLoginRequest(AppBaseModel):
    """Login model."""

    username: str
    password: SecretStr


class UserResponse(UserBase):
    """User response model omitting password entirely."""

    id: uuid.UUID = Field(..., strict=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class User(UserResponse):
    """Internal user domain model extending UserResponse with hashed_password."""

    hashed_password: str = ""


class TokenResponse(AppBaseModel):
    """JWT Token response."""

    access_token: str
    token_type: str = "bearer"
    user_id: uuid.UUID | None = Field(default=None, strict=False)
    username: str | None = None


class AdminStatsResponse(AppBaseModel):
    """Platform statistics."""

    total_users: int
    total_films: int
    total_reviews: int
    uptime_status: str = "healthy"
