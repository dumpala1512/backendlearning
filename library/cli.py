"""
Command-Line Interface (CLI) entry point for the Library Management System.

Acts as the top-level exception handler: catches all domain exceptions,
displays clean, friendly error messages, and ensures no Python tracebacks are shown.
"""

from pathlib import Path
import sys

# Support running directly via 'python cli.py' or 'uv run cli.py' from inside library/
current_dir = Path(__file__).resolve().parent
if str(current_dir.parent) not in sys.path:
    sys.path.insert(0, str(current_dir.parent))

from library.exceptions import (
    BusinessRuleViolationError,
    InvalidInputError,
    LibraryError,
    ResourceNotFoundError,
)
from library.services import (
    calculate_loan_fine,
    find_book_by_isbn,
    get_books_by_author,
    has_overdue_loans,
    process_books,
    sort_by_publication_year,
    sort_by_title,
)
from library.session import CatalogueSession


class LibraryCLI:
    """CLI application runner wrapping user actions with top-level error handling."""

    def __init__(self, session: CatalogueSession) -> None:
        self.session: CatalogueSession = session

    def show_menu(self) -> None:
        """Displays interactive menu options."""
        print("\n--- Library Catalogue Menu ---")
        print("  [1] List all books")
        print("  [2] Search book by ISBN")
        print("  [3] Search books by author")
        print("  [4] Check member overdue status")
        print("  [5] Calculate loan fine")
        print("  [6] Sort books by title")
        print("  [7] Sort books by publication year")
        print("  [8] Exit")

    def run(self) -> None:
        """Interactive loop with top-level error handling (zero tracebacks)."""
        while True:
            self.show_menu()
            choice = input("\nEnter choice (1-8): ").strip()

            try:
                if choice == "1":
                    print(f"\n{'ISBN':<18} | {'Title':<26} | {'Author':<20} | {'Year'}")
                    print("-" * 75)
                    for b in self.session.books:
                        print(f"{b.isbn:<18} | {b.title:<26} | {b.author:<20} | {b.year}")

                elif choice == "2":
                    isbn = input("Enter ISBN to search (e.g. 978-0451524935): ").strip()
                    book = find_book_by_isbn(isbn, self.session.books)
                    print(f"\nFound: {book}")

                elif choice == "3":
                    author = input("Enter author name (e.g. George Orwell): ").strip()
                    books_found = get_books_by_author(author, self.session.books)
                    if not books_found:
                        print(f"No books found by author '{author}'.")
                    else:
                        print(f"\nBooks by '{author}':")
                        for b in books_found:
                            print(f"  * {b}")

                elif choice == "4":
                    mid = input("Enter Member ID (M001, M002, M003): ").strip().upper()
                    matching_members = [m for m in self.session.members if m.member_id == mid]
                    if not matching_members:
                        raise ResourceNotFoundError(resource_type="Member", resource_id=mid)

                    member = matching_members[0]
                    is_overdue = has_overdue_loans(member, self.session.loans)
                    status_text = "HAS OVERDUE BOOKS" if is_overdue else "Clear (No overdue books)"
                    print(f"\nMember: {member.name} (ID: {member.member_id}) -> Status: {status_text}")

                elif choice == "5":
                    loan_id = input("Enter Loan ID (L101, L102, L103, L104): ").strip().upper()
                    matching_loans = [l for l in self.session.loans if l.loan_id == loan_id]
                    if not matching_loans:
                        raise ResourceNotFoundError(resource_type="Loan", resource_id=loan_id)

                    loan = matching_loans[0]
                    fine = calculate_loan_fine(loan)
                    print(f"\nLoan [{loan.loan_id}] - Book: '{loan.book.title}' | Borrower: {loan.member.name}")
                    print(f"Due Date: {loan.due_date} | Return Date: {loan.return_date}")
                    print(f"Fine Owed: ${fine:.2f}")

                elif choice == "6":
                    sorted_books = process_books(self.session.books, sort_by_title)
                    print("\nBooks Sorted Alphabetically by Title:")
                    for b in sorted_books:
                        print(f"  * {b.title} by {b.author}")

                elif choice == "7":
                    sorted_books = process_books(self.session.books, sort_by_publication_year)
                    print("\nBooks Sorted Chronologically by Year:")
                    for b in sorted_books:
                        print(f"  * {b.year}: {b.title} by {b.author}")

                elif choice == "8":
                    print("\nExiting library session. Goodbye!")
                    break

                else:
                    raise InvalidInputError(
                        field_name="menu_choice",
                        invalid_value=choice,
                        reason="Please select a valid option between 1 and 8.",
                    )

            except ResourceNotFoundError as e:
                print(f"\n[NOT FOUND] {e}")
            except BusinessRuleViolationError as e:
                print(f"\n[RULE VIOLATION] {e}")
            except InvalidInputError as e:
                print(f"\n[INVALID INPUT] {e}")
            except LibraryError as e:
                print(f"\n[DOMAIN ERROR] {e}")
            except (KeyboardInterrupt, EOFError):
                print("\n\nSession interrupted by user. Exiting cleanly...")
                break
            except Exception as e:
                # Top-level generic safety net (never expose raw Python traceback)
                print(f"\n[SYSTEM NOTICE] An unexpected error occurred: {e}")


def main() -> None:
    """Main CLI entry point wrapping interactive session inside CatalogueSession context manager."""
    with CatalogueSession() as session:
        cli = LibraryCLI(session)
        cli.run()


if __name__ == "__main__":
    main()
