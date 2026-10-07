from __future__ import annotations

from typing import Any
import uuid
from fastapi import status

from app.exceptions.base import (
    AuthenticationError,
    DuplicateEntityError,
    EntityNotFoundError,
)


class UserNotFoundError(EntityNotFoundError):
    """Raised when a specific User cannot be found (HTTP 404)."""

    status_code: int = status.HTTP_404_NOT_FOUND
    default_message: str = "User not found."

    def __init__(
        self,
        identifier: uuid.UUID | str | None = None,
        *,
        user_id: uuid.UUID | str | None = None,
        username: str | None = None,
        email: str | None = None,
        message: str | None = None,
        detail: dict[str, Any] | None = None,
        status_code: int | None = None,
    ) -> None:
        if identifier is not None:
            if isinstance(identifier, str) and (" " in identifier or identifier.startswith("No user")):
                message = message or identifier
            elif isinstance(identifier, uuid.UUID):
                user_id = user_id or identifier
            elif isinstance(identifier, str):
                if "@" in identifier:
                    email = email or identifier
                else:
                    user_id = user_id or identifier

        self.user_id = user_id
        self.username = username
        self.email = email

        details: dict[str, Any] = {}
        if user_id:
            details["user_id"] = str(user_id)
        if username:
            details["username"] = username
        if email:
            details["email"] = email
        details.update(detail or {})

        msg = (
            message
            or (f"User with id {user_id} not found." if user_id
                else f"User with username '{username}' not found." if username
                else f"User with email '{email}' not found." if email
                else self.default_message)
        )
        super().__init__(message=msg, detail=details, status_code=status_code)


class UserAlreadyExistsError(DuplicateEntityError):
    """Raised when attempting to register a user with an existing username or email (HTTP 409)."""

    status_code: int = status.HTTP_409_CONFLICT
    default_message: str = "A user with the given username or email already exists."

    def __init__(
        self,
        field: str = "username",
        value: str = "",
        message: str | None = None,
        detail: dict[str, Any] | None = None,
        status_code: int | None = None,
    ) -> None:
        self.field = field
        self.value = value
        details: dict[str, Any] = {field: value} if value else {}
        details.update(detail or {})
        super().__init__(
            message=message or f"User with {field} '{value}' already exists.",
            detail=details,
            status_code=status_code,
        )


class InvalidCredentialsError(AuthenticationError):
    """Raised when username or password authentication fails (HTTP 401)."""

    status_code: int = status.HTTP_401_UNAUTHORIZED
    default_message: str = "Invalid username or password credentials provided."


class InvalidTokenError(AuthenticationError):
    """Raised when JWT token decoding or claim validation fails (HTTP 401)."""

    status_code: int = status.HTTP_401_UNAUTHORIZED
    default_message: str = "Invalid, malformed, or unauthorized token provided."


class TokenExpiredError(AuthenticationError):
    """Raised when JWT access or refresh token has expired (HTTP 401)."""

    status_code: int = status.HTTP_401_UNAUTHORIZED
    default_message: str = "Token has expired."


class TokenReusedError(AuthenticationError):
    """Raised when an already-used or revoked refresh token is presented (HTTP 401)."""

    status_code: int = status.HTTP_401_UNAUTHORIZED
    default_message: str = "Refresh token has already been used or revoked."

