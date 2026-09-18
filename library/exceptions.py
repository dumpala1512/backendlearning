"""
Custom domain exceptions for the Library Management System.

All exceptions carry typed attributes describing the specific problem,
replacing sentinel return values (None, False) across the application.
"""

from typing import Any


class LibraryError(Exception):
    """Base class for all library domain exceptions."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message: str = message

    def __str__(self) -> str:
        return self.message


class ResourceNotFoundError(LibraryError):
    """
    Raised when a requested resource (Book, Member, Loan) cannot be found.
    """

    def __init__(self, resource_type: str, resource_id: int | str) -> None:
        self.resource_type: str = str(resource_type)
        self.resource_id: int | str = resource_id
        super().__init__(f"{self.resource_type} with ID '{self.resource_id}' was not found.")


class BusinessRuleViolationError(LibraryError):
    """
    Raised when an operation violates library policies or business constraints.
    Examples: book already borrowed, maximum loan limit reached, book not on loan.
    """

    def __init__(self, rule: str, details: str) -> None:
        self.rule: str = rule
        self.details: str = details
        super().__init__(f"Business rule violation [{self.rule}]: {self.details}")


# Alias for backwards compatibility
BusinessRuleError = BusinessRuleViolationError


class InvalidInputError(LibraryError):
    """
    Raised whenever supplied input data fails validation checks.
    Examples: empty title, negative ID, invalid ISBN, invalid menu selection.
    """

    def __init__(self, field_name: str, invalid_value: Any, reason: str = "") -> None:
        self.field_name: str = field_name
        self.invalid_value: Any = invalid_value
        self.reason: str = reason
        # Aliases for flexibility
        self.field: str = field_name
        self.value: Any = invalid_value

        msg: str = f"Invalid value for '{field_name}' ({invalid_value!r})"
        if reason:
            msg += f": {reason}"
        super().__init__(msg)
