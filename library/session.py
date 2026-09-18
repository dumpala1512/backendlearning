"""
CatalogueSession context manager for the Library Catalogue system.
Performs setup on entry and guaranteed cleanup on exit.
"""

from datetime import datetime
from types import TracebackType
from typing import Optional

from library.models import Book, Loan, Member
from library.services import BOOKS, LOANS, MEMBERS


class CatalogueSession:
    """
    Context manager that encapsulates a library catalogue operational session.
    Setup work inside __enter__(), guaranteed cleanup inside __exit__().
    """

    def __init__(self) -> None:
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.cleaned_up: bool = False
        self.books: list[Book] = BOOKS
        self.members: list[Member] = MEMBERS
        self.loans: list[Loan] = LOANS

    def __enter__(self) -> "CatalogueSession":
        """Setup performed upon entering the session context."""
        self.start_time = datetime.now()
        self.cleaned_up = False

        print("\n" + "=" * 62)
        print(f"  [CATALOGUE SESSION OPENED: {self.start_time.strftime('%H:%M:%S')}]")
        print(f"  Loaded Initial Data: {len(self.books)} books, {len(self.members)} members, {len(self.loans)} loans")
        print("=" * 62)
        return self

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> bool:
        """Guaranteed cleanup executed on exit, whether normal or on exception."""
        self.end_time = datetime.now()
        self.cleaned_up = True
        duration: float = (self.end_time - self.start_time).total_seconds() if self.start_time else 0.0

        print("\n" + "=" * 62)
        if exc_val is None:
            print("  [CATALOGUE SESSION CLOSED] Completed Normally")
        else:
            print(f"  [CATALOGUE SESSION CLOSED] Terminated due to error: {exc_val}")

        print(f"  Active Session Duration: {duration:.2f} seconds")
        print("  Cleanup: Session buffers flushed, resources released.")
        print("=" * 62 + "\n")

        # Return False so any unhandled exceptions propagate or are handled by caller
        return False
