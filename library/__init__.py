"""
Library Catalogue Package.

Exposes domain models, services, custom exceptions, and context manager session.
"""

from library.exceptions import (
    BusinessRuleViolationError,
    InvalidInputError,
    LibraryError,
    ResourceNotFoundError,
)
from library.models import Book, Loan, Member, PremiumMember
from library.services import (
    BOOKS,
    LOANS,
    MEMBERS,
    calculate_loan_fine,
    find_book_by_isbn,
    get_books_by_author,
    has_overdue_loans,
    process_books,
    sort_by_publication_year,
    sort_by_title,
)
from library.session import CatalogueSession

__all__ = [
    # Models
    "Book",
    "Member",
    "PremiumMember",
    "Loan",
    # Data
    "BOOKS",
    "MEMBERS",
    "LOANS",
    # Functions
    "find_book_by_isbn",
    "get_books_by_author",
    "has_overdue_loans",
    "calculate_loan_fine",
    "process_books",
    "sort_by_title",
    "sort_by_publication_year",
    # Session
    "CatalogueSession",
    # Exceptions
    "LibraryError",
    "ResourceNotFoundError",
    "BusinessRuleViolationError",
    "InvalidInputError",
]
