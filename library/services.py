"""
Business logic services for the Library Management System.
Contains the domain functions operating on Book, Member, and Loan instances.
Replaces sentinel return values (e.g. None) with custom typed exceptions.
"""

from datetime import date
from typing import Callable, Optional

from library.exceptions import BusinessRuleViolationError, InvalidInputError, ResourceNotFoundError
from library.models import Book, Loan, Member, PremiumMember


# =====================================================================
# HARDCODED INITIAL DATA (TYPED DATACLASS INSTANCES)
# =====================================================================

BOOKS: list[Book] = [
    Book(isbn="978-0141439518", title="Pride and Prejudice", author="Jane Austen", year=1813),
    Book(isbn="978-0451524935", title="1984", author="George Orwell", year=1949),
    Book(isbn="978-0060850524", title="Brave New World", author="Aldous Huxley", year=1932),
    Book(isbn="978-0451526342", title="Animal Farm", author="George Orwell", year=1945),
    Book(isbn="978-0743273565", title="The Great Gatsby", author="F. Scott Fitzgerald", year=1925),
]

MEMBERS: list[Member] = [
    Member(member_id="M001", name="Alice Johnson", email="alice@example.com"),
    Member(member_id="M002", name="Bob Smith", email="bob@example.com"),
    PremiumMember(member_id="M003", name="Charlie Davis", email="charlie@example.com", membership_tier="Platinum"),
]

# Quick lookup maps for building initial loan records
_books_by_isbn: dict[str, Book] = {b.isbn: b for b in BOOKS}
_members_by_id: dict[str, Member] = {m.member_id: m for m in MEMBERS}

LOANS: list[Loan] = [
    Loan(
        loan_id="L101",
        book=_books_by_isbn["978-0451524935"],  # 1984
        member=_members_by_id["M001"],          # Alice Johnson
        loan_date=date(2026, 8, 1),
        due_date=date(2026, 8, 15),
        return_date=None,                       # Overdue
    ),
    Loan(
        loan_id="L102",
        book=_books_by_isbn["978-0141439518"],  # Pride and Prejudice
        member=_members_by_id["M001"],          # Alice Johnson
        loan_date=date(2026, 9, 1),
        due_date=date(2026, 9, 20),
        return_date=None,                       # Active, on time
    ),
    Loan(
        loan_id="L103",
        book=_books_by_isbn["978-0060850524"],  # Brave New World
        member=_members_by_id["M002"],          # Bob Smith
        loan_date=date(2026, 8, 10),
        due_date=date(2026, 8, 24),
        return_date=date(2026, 8, 22),          # Returned on time
    ),
    Loan(
        loan_id="L104",
        book=_books_by_isbn["978-0451526342"],  # Animal Farm
        member=_members_by_id["M003"],          # Charlie Davis (Premium)
        loan_date=date(2026, 8, 5),
        due_date=date(2026, 8, 19),
        return_date=None,                       # Overdue
    ),
]


# =====================================================================
# CORE FUNCTIONS (REFACTORED WITH CUSTOM DOMAIN EXCEPTIONS)
# =====================================================================

def find_book_by_isbn(isbn: str, books: list[Book]) -> Book:
    """
    Look up a Book instance by its ISBN.

    Replaces returning None with raising ResourceNotFoundError when missing,
    and InvalidInputError if the ISBN is blank.
    """
    clean_isbn = isbn.strip()
    if not clean_isbn:
        raise InvalidInputError(field_name="isbn", invalid_value=isbn, reason="ISBN cannot be empty.")

    for book in books:
        if book.isbn == clean_isbn:
            return book

    # Replaced sentinel `return None` with custom domain exception
    raise ResourceNotFoundError(resource_type="Book", resource_id=clean_isbn)


def get_books_by_author(author: str, books: Optional[list[Book]] = None) -> list[Book]:
    """
    Find and return all Book instances by a specific author (case-insensitive).

    Raises InvalidInputError if the author string is empty.
    """
    target_author: str = author.strip().lower()
    if not target_author:
        raise InvalidInputError(field_name="author", invalid_value=author, reason="Author cannot be empty.")

    book_list = books if books is not None else BOOKS
    return [
        book for book in book_list
        if book.author.strip().lower() == target_author
    ]


def has_overdue_loans(
    member: Member,
    loans: list[Loan],
    reference_date: Optional[date] = None,
) -> bool:
    """
    Check whether a given Member instance has any active loans that are past due.
    Leverages the Loan's dates or is_overdue property.
    """
    if not isinstance(member, Member):
        raise InvalidInputError(field_name="member", invalid_value=member, reason="Must be a valid Member instance.")

    for loan in loans:
        if loan.member.member_id == member.member_id:
            if reference_date is not None:
                if loan.is_overdue_as_of(reference_date):
                    return True
            else:
                if loan.is_overdue:
                    return True
    return False


def calculate_loan_fine(
    loan: Loan,
    reference_date: Optional[date] = None,
    daily_rate: float = 0.50,
) -> float:
    """
    Calculate the fine owed for an overdue Loan instance.
    If the book has not been returned and the due date is in the past:
        fine = overdue_days * daily_rate
    Otherwise, fine is 0.0.

    Raises InvalidInputError if daily_rate is negative.
    """
    if daily_rate < 0:
        raise InvalidInputError(field_name="daily_rate", invalid_value=daily_rate, reason="Daily rate cannot be negative.")

    if loan.return_date is not None:
        return 0.0

    current_date: date = reference_date if reference_date is not None else date.today()

    if loan.due_date >= current_date:
        return 0.0

    overdue_days: int = (current_date - loan.due_date).days
    return round(overdue_days * daily_rate, 2)


# =====================================================================
# HIGHER-ORDER FUNCTION & TRANSFORMERS
# =====================================================================

def process_books(
    books: list[Book],
    transform_fn: Callable[[list[Book]], list[Book]],
) -> list[Book]:
    """
    Accepts a list of Book instances and a transformer callable.
    Applies the callable to transform, filter, or sort the books,
    and returns the resulting list.
    """
    if not callable(transform_fn):
        raise InvalidInputError(
            field_name="transform_fn",
            invalid_value=transform_fn,
            reason="Transformer parameter must be callable.",
        )
    return transform_fn(books)


def sort_by_title(books: list[Book]) -> list[Book]:
    """Sort books alphabetically by title."""
    return sorted(books, key=lambda b: b.title)


def sort_by_publication_year(books: list[Book]) -> list[Book]:
    """Sort books chronologically by publication year."""
    return sorted(books, key=lambda b: b.year)
