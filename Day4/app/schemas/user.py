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
    """Login model accepting either username or email (neither requires the other)."""

    username: str | None = Field(
        default=None,
        description="Username or email address (provide either username or email)",
    )
    email: str | None = Field(
        default=None,
        description="Email address (optional if username is provided)",
    )
    password: SecretStr = Field(
        ...,
        description="User password",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "username": "bob_builder",
                    "password": "CanWeFixIt123!",
                },
                {
                    "email": "bob@example.com",
                    "password": "CanWeFixIt123!",
                },
            ]
        }
    }

    @model_validator(mode="before")
    @classmethod
    def resolve_identifiers(cls, data: object) -> object:
        if isinstance(data, dict):
            # Check for alternative aliases like identifier or username_or_email
            ident = data.get("identifier") or data.get("username_or_email")
            if ident and not data.get("username") and not data.get("email"):
                if "@" in str(ident):
                    data["email"] = str(ident).strip()
                else:
                    data["username"] = str(ident).strip()

            # Normalize empty strings or whitespace to None so neither field is forced
            if "email" in data and isinstance(data["email"], str) and not data["email"].strip():
                data["email"] = None
            if "username" in data and isinstance(data["username"], str) and not data["username"].strip():
                data["username"] = None

            # If username looks like an email and email is not provided, also populate email
            username_val = data.get("username")
            if username_val and "@" in str(username_val) and not data.get("email"):
                data["email"] = str(username_val).strip()

        return data

    @model_validator(mode="after")
    def validate_identifier(self) -> "UserLoginRequest":
        if not self.username and not self.email:
            raise ValueError("Either username or email must be provided.")
        return self


class RefreshTokenRequest(AppBaseModel):
    """Payload for refreshing an access token."""

    refresh_token: str = Field(..., min_length=10, description="The refresh token string")


class AuthenticatedUser(AppBaseModel):
    """Stateless authenticated user identity derived directly from validated JWT claims."""

    id: uuid.UUID = Field(..., strict=False)
    username: str
    role: str = "user"
    email: str | None = None


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
    refresh_token: str | None = None
    token_type: str = "bearer"
    user_id: uuid.UUID | None = Field(default=None, strict=False)
    username: str | None = None
    role: str | None = None


class AdminStatsResponse(AppBaseModel):
    """Platform statistics."""

    total_users: int
    total_films: int
    total_reviews: int
    uptime_status: str = "healthy"
