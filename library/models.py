"""
Domain models for the Library Management System.
Uses Python dataclasses for all core entities with complete type annotations.
"""

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class Book:
    """Represents a book in the library catalogue."""
    isbn: str
    title: str
    author: str
    year: int = 2026

    def __str__(self) -> str:
        return f"'{self.title}' by {self.author} ({self.year}) [ISBN: {self.isbn}]"


@dataclass
class Member:
    """Represents a standard library member with a default borrowing period of 14 days."""
    member_id: str
    name: str
    email: str
    loan_period_days: int = 14

    def __str__(self) -> str:
        return f"{self.name} (ID: {self.member_id}, Period: {self.loan_period_days} days)"


@dataclass
class PremiumMember(Member):
    """Represents a premium library member with a 30-day loan period and a membership tier."""
    loan_period_days: int = 30
    membership_tier: str = "Gold"

    def __str__(self) -> str:
        return (
            f"{self.name} [{self.membership_tier} Premium] "
            f"(ID: {self.member_id}, Period: {self.loan_period_days} days)"
        )


@dataclass
class Loan:
    """Represents a borrowing record between a Member and a Book."""
    loan_id: str
    book: Book
    member: Member
    loan_date: date
    due_date: date
    return_date: Optional[date] = None

    @property
    def is_overdue(self) -> bool:
        """Computed property: returns True if unreturned and due date has passed."""
        if self.return_date is not None:
            return False
        return date.today() > self.due_date

    def is_overdue_as_of(self, reference_date: date) -> bool:
        """Check overdue status against an explicit reference date."""
        if self.return_date is not None:
            return False
        return reference_date > self.due_date

    def __repr__(self) -> str:
        status: str = "Returned" if self.return_date else ("OVERDUE" if self.is_overdue else "Active")
        return (
            f"Loan(id='{self.loan_id}', book='{self.book.title}', "
            f"member='{self.member.name}', due={self.due_date}, status='{status}')"
        )
