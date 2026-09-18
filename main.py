"""
Main entry point for the Library Catalogue application.
Executes the CLI wrapped inside the CatalogueSession context manager.
"""

from library.cli import main

if __name__ == "__main__":
    main()
