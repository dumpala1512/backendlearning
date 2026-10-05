from __future__ import annotations


class DomainError(Exception):
    """Base exception for all domain-level business errors."""

    def __init__(self, message: str = "A domain error occurred"):
        self.message = message
        super().__init__(self.message)


class EntityNotFoundError(DomainError):
    """Raised when an entity requested from the database is not found."""

    def __init__(self, message: str = "Entity not found"):
        super().__init__(message)


class FilmNotFoundError(EntityNotFoundError):
    """Raised when a specific Film is not found."""

    def __init__(self, message: str = "Film not found"):
        super().__init__(message)


class ReviewNotFoundError(EntityNotFoundError):
    """Raised when a specific Review is not found."""

    def __init__(self, message: str = "Review not found"):
        super().__init__(message)


class UserNotFoundError(EntityNotFoundError):
    """Raised when a specific User is not found."""

    def __init__(self, message: str = "User not found"):
        super().__init__(message)


class DuplicateEntityError(DomainError):
    """Raised when an operation violates uniqueness or business identity constraints."""

    def __init__(self, message: str = "Entity already exists"):
        super().__init__(message)
