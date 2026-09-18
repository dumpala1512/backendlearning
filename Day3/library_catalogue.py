"""
Library Catalogue - Object-Oriented Domain Model
Refactored to use @dataclass across all domain entities.

Concepts demonstrated:
1. Dataclasses everywhere (@dataclass for Book, Member, PremiumMember, and Loan).
2. Default values and clean typed instance attributes.
3. Inheritance with dataclasses and explicit super().__init__() call in PremiumMember.
4. Computed Properties (@property is_overdue) deriving status without storing a boolean flag.
5. Informative, single-line string & repr representations.
6. Type-safe functions operating on class instances rather than raw dictionaries.
"""

from dataclasses import dataclass
from datetime import date
from typing import Callable, Optional


# =====================================================================
# 1. DOMAIN CLASSES (ALL USING @dataclass)
# =====================================================================

@dataclass
class Book:
    """
    Represents a book in the library catalogue.
    Uses @dataclass for concise attribute definitions, typed fields, and automatic repr.
    """
    isbn: str
    title: str
    author: str
    year: int = 2026

    def __str__(self) -> str:
        return f"'{self.title}' by {self.author} ({self.year}) [ISBN: {self.isbn}]"


@dataclass
class Member:
    """
    Represents a standard library member with a default borrowing period of 14 days.
    """
    member_id: str
    name: str
    email: str 
    loan_period_days: int = 14

    def __str__(self) -> str:
        return f"{self.name} (ID: {self.member_id}, Period: {self.loan_period_days} days)"


@dataclass
class PremiumMember(Member):
    """
    Represents a premium library member.
    Inherits from Member using dataclass inheritance, overriding the default
    loan period to 30 days and adding a membership tier.
    """
    loan_period_days: int = 30
    membership_tier: str = "Gold"

    def __str__(self) -> str:
        return (
            f"{self.name} [{self.membership_tier} Premium] "
            f"(ID: {self.member_id}, Period: {self.loan_period_days} days)"
        )


@dataclass
class Loan:
    """
    Represents a borrowing record between a Member and a Book.
    Captures loan date, due date, and an optional return date.
    """
    loan_id: str
    book: Book
    member: Member
    loan_date: date
    due_date: date
    return_date: Optional[date] = None

    @property
    def is_overdue(self) -> bool:
        """
        Computed property that derives whether the loan is overdue
        directly from the stored dates without storing a boolean flag.
        A loan is overdue if not returned and the due date has passed today.
        """
        if self.return_date is not None:
            return False
        return date.today() > self.due_date

    def is_overdue_as_of(self, reference_date: date) -> bool:
        """
        Check overdue status against an explicit reference date.
        """
        if self.return_date is not None:
            return False
        return reference_date > self.due_date

    def __repr__(self) -> str:
        status: str = "Returned" if self.return_date else ("OVERDUE" if self.is_overdue else "Active")
        return (
            f"Loan(id='{self.loan_id}', book='{self.book.title}', "
            f"member='{self.member.name}', due={self.due_date}, status='{status}')"
        )


# =====================================================================
# 2. HARDCODED TEST DATA (TYPED DATACLASS INSTANCES)
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

# Map by ISBN and member_id for convenient lookup when constructing test loans
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
# 3. TYPED CORE FUNCTIONS (OPERATING ON DATACLASS INSTANCES)
# =====================================================================

def find_book_by_isbn(isbn: str, books: list[Book]) -> Optional[Book]:
    """
    Look up a Book instance by its ISBN.
    Returns the matching Book, or None if no book is found.
    """
    for book in books:
        if book.isbn == isbn:
            return book
    return None


def get_books_by_author(author: str) -> list[Book]:
    """
    Find and return all Book instances by a specific author (case-insensitive).
    """
    target_author: str = author.strip().lower()
    return [
        book for book in BOOKS
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
    """
    if loan.return_date is not None:
        return 0.0

    current_date: date = reference_date if reference_date is not None else date.today()

    if loan.due_date >= current_date:
        return 0.0

    overdue_days: int = (current_date - loan.due_date).days
    return round(overdue_days * daily_rate, 2)


# =====================================================================
# 4. HIGHER-ORDER FUNCTION (CALLABLE PARAMETER)
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
    return transform_fn(books)


# Sample transformer callables
def sort_by_title(books: list[Book]) -> list[Book]:
    """Sort books alphabetically by title."""
    return sorted(books, key=lambda b: b.title)


def sort_by_publication_year(books: list[Book]) -> list[Book]:
    """Sort books chronologically by publication year."""
    return sorted(books, key=lambda b: b.year)


# =====================================================================
# 5. FORMATTED REPORT / ENTRY POINT
# =====================================================================

def print_separator(char: str = "-", length: int = 60) -> None:
    print(char * length)


def main() -> None:
    """
    Demonstrate each typed function using dataclass instances
    and print a clean, readable report.
    """
    reference_date: date = date.today()

    print("=" * 60)
    print("      PUBLIC LIBRARY CATALOGUE - DOMAIN MODEL REPORT")
    print(f"      Reference Date for Analysis: {reference_date}")
    print("=" * 60)

    # 0. Demonstrate Dataclass Representations
    print("\n0. DATACLASS REPRESENTATIONS (__repr__)")
    print_separator()
    print(f"Book Dataclass          : {repr(BOOKS[0])}")
    print(f"Member Dataclass        : {repr(MEMBERS[0])}")
    print(f"PremiumMember Dataclass : {repr(MEMBERS[2])}")
    print(f"Loan Dataclass          : {repr(LOANS[0])}")

    # 1. Look up book by ISBN (both existing and non-existing)
    print("\n1. LOOK UP BOOK BY ISBN")
    print_separator()

    isbn_to_search: str = "978-0451524935"
    book_found: Optional[Book] = find_book_by_isbn(isbn_to_search, BOOKS)
    print(f"Lookup for existing ISBN '{isbn_to_search}':")
    if book_found is not None:
        print(f"  -> Title : {book_found.title}")
        print(f"  -> Author: {book_found.author}")
        print(f"  -> Year  : {book_found.year}")
        print(f"  -> String: {book_found}")
    else:
        print("  -> Book not found.")

    missing_isbn: str = "978-0000000000"
    book_missing: Optional[Book] = find_book_by_isbn(missing_isbn, BOOKS)
    print(f"\nLookup for non-existent ISBN '{missing_isbn}':")
    if book_missing is not None:
        print(f"  -> Found: {book_missing.title}")
    else:
        print("  -> Result: None (Book not found as expected)")

    # 2. List books by author
    print("\n2. LIST BOOKS BY AUTHOR")
    print_separator()

    author_name: str = "George Orwell"
    orwell_books: list[Book] = get_books_by_author(author_name)
    print(f"Books by '{author_name}' ({len(orwell_books)} found):")
    for b in orwell_books:
        print(f"  * {b}")

    # 3. Check for overdue loans per member
    print("\n3. MEMBER OVERDUE STATUS")
    print_separator()

    for member in MEMBERS:
        overdue: bool = has_overdue_loans(member, LOANS, reference_date)
        status_text: str = "HAS OVERDUE BOOKS" if overdue else "Clear (No overdue books)"
        print(f"Member: {member.name:<16} (ID: {member.member_id}) -> Status: {status_text}")
        print(f"        Borrowing allowance: {member.loan_period_days} days")

    # 4. Calculate fine for overdue loans
    print("\n4. FINE CALCULATION & COMPUTED PROPERTY FOR LOANS")
    print_separator()

    daily_fine_rate: float = 0.50
    print(f"Configured Daily Overdue Rate: ${daily_fine_rate:.2f}/day\n")

    for loan in LOANS:
        fine: float = calculate_loan_fine(loan, reference_date, daily_fine_rate)

        if loan.return_date is not None:
            status_desc: str = f"Returned on {loan.return_date}"
        elif loan.is_overdue:
            days_late: int = (reference_date - loan.due_date).days
            status_desc: str = f"OVERDUE by {days_late} days (Due: {loan.due_date})"
        else:
            status_desc: str = f"Active, on time (Due: {loan.due_date})"

        print(f"Loan [{loan.loan_id}] - '{loan.book.title}' borrowed by {loan.member.name}")
        print(f"  Computed .is_overdue: {loan.is_overdue}")
        print(f"  Status              : {status_desc}")
        print(f"  Fine Owed           : ${fine:.2f}")

    # 5. Higher-order function transformation
    print("\n5. HIGHER-ORDER FUNCTION: TRANSFORM & SORT BOOKS")
    print_separator()

    sorted_by_title_books: list[Book] = process_books(BOOKS, sort_by_title)
    print("Books Sorted Alphabetically by Title:")
    for b in sorted_by_title_books:
        print(f"  * {b.title} - {b.author} ({b.year})")

    print("\nBooks Sorted Chronologically by Year:")
    sorted_by_year_books: list[Book] = process_books(BOOKS, sort_by_publication_year)
    for b in sorted_by_year_books:
        print(f"  * {b.year}: {b.title} by {b.author}")

    print("\n" + "=" * 60)
    print("                     END OF REPORT")
    print("=" * 60)


if __name__ == "__main__":
    main()
