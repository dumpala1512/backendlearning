from __future__ import annotations

from typing import Any
from fastapi import status


class DomainError(Exception):
    """
    Base domain-level exception for all business logic errors.
    Carries an explicit HTTP status code, descriptive error message,
    structured error details, and a machine-readable error type.
    """

    status_code: int = status.HTTP_400_BAD_REQUEST
    default_message: str = "A domain business logic error occurred."

    def __init__(
        self,
        message: str | None = None,
        detail: dict[str, Any] | None = None,
        status_code: int | None = None,
    ) -> None:
        self.message: str = message if message is not None else self.default_message
        self.detail: dict[str, Any] = detail or {}
        if status_code is not None:
            self.status_code = status_code
        super().__init__(self.message)

    @property
    def error_type(self) -> str:
        """Returns the type name, stripping 'Error' suffix if present for clean API types."""
        name = self.__class__.__name__
        return name[:-5] if name.endswith("Error") else name

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to standard dictionary representation."""
        return {
            "status_code": self.status_code,
            "type": self.error_type,
            "message": self.message,
            "detail": self.detail,
        }

    def __str__(self) -> str:
        return self.message

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"status_code={self.status_code}, "
            f"message={self.message!r}, "
            f"detail={self.detail})"
        )


class EntityNotFoundError(DomainError):
    """Raised when a requested resource entity is not found in the database (HTTP 404)."""

    status_code: int = status.HTTP_404_NOT_FOUND
    default_message: str = "Requested resource was not found."


class DuplicateEntityError(DomainError):
    """Raised when an operation violates business uniqueness constraints (HTTP 409)."""

    status_code: int = status.HTTP_409_CONFLICT
    default_message: str = "Resource already exists or uniqueness constraint was violated."


class PermissionDeniedError(DomainError):
    """Raised when a user lacks permission to perform a domain action (HTTP 403)."""

    status_code: int = status.HTTP_403_FORBIDDEN
    default_message: str = "Permission denied: you do not have permission to perform this action."


class ValidationError(DomainError):
    """Raised when domain-level business validation fails (HTTP 400)."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    default_message: str = "Validation failed: invalid input data or business constraint violated."


class AuthenticationError(DomainError):
    """Raised when user authentication or credentials verification fails (HTTP 401)."""

    status_code: int = status.HTTP_401_UNAUTHORIZED
    default_message: str = "Authentication failed: invalid or missing credentials."

