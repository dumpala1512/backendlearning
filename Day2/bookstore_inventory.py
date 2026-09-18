# ==============================================================================
# Exercise: Bookstore Inventory Analyser
# A clear, beginner-friendly script to analyse book inventory in memory.
# ==============================================================================

# ------------------------------------------------------------------------------
# 1. Initial Book Inventory
# A list of dictionaries representing books in stock (including some duplicates).
# ------------------------------------------------------------------------------
books = [
    {"title": "The Great Gatsby", "author": "F. Scott Fitzgerald", "genre": "Fiction", "year": 1925, "price": 10.99},
    {"title": "To Kill a Mockingbird", "author": "Harper Lee", "genre": "Fiction", "year": 1960, "price": 12.49},
    {"title": "1984", "author": "George Orwell", "genre": "Fiction", "year": 1949, "price": 9.99},
    {"title": "Animal Farm", "author": "George Orwell", "genre": "Fiction", "year": 1945, "price": 8.99},
    {"title": "1984", "author": "George Orwell", "genre": "Fiction", "year": 1949, "price": 9.99},  # Duplicate
    {"title": "Dune", "author": "Frank Herbert", "genre": "Science Fiction", "year": 1965, "price": 14.99},
    {"title": "Neuromancer", "author": "William Gibson", "genre": "Science Fiction", "year": 1984, "price": 11.50},
    {"title": "Foundation", "author": "Isaac Asimov", "genre": "Science Fiction", "year": 1951, "price": 13.20},
    {"title": "Project Hail Mary", "author": "Andy Weir", "genre": "Science Fiction", "year": 2021, "price": 16.99},
    {"title": "Dune", "author": "Frank Herbert", "genre": "Science Fiction", "year": 1965, "price": 14.99},  # Duplicate
    {"title": "The Silent Patient", "author": "Alex Michaelides", "genre": "Mystery", "year": 2019, "price": 13.99},
    {"title": "Gone Girl", "author": "Gillian Flynn", "genre": "Mystery", "year": 2012, "price": 11.99},
    {"title": "The Da Vinci Code", "author": "Dan Brown", "genre": "Mystery", "year": 2003, "price": 10.50},
    {"title": "Sapiens", "author": "Yuval Noah Harari", "genre": "Non-Fiction", "year": 2011, "price": 18.00},
    {"title": "Educated", "author": "Tara Westover", "genre": "Non-Fiction", "year": 2018, "price": 15.75},
    {"title": "Atomic Habits", "author": "James Clear", "genre": "Non-Fiction", "year": 2018, "price": 16.50},
    {"title": "Thinking, Fast and Slow", "author": "Daniel Kahneman", "genre": "Non-Fiction", "year": 2011, "price": 14.00},
]

print("=" * 60)
print("       BOOKSTORE INVENTORY ANALYSER (IN-MEMORY STOCK)")
print("=" * 60)
print(f"Total initial records in stock: {len(books)}\n")

# ------------------------------------------------------------------------------
# STEP 1: De-duplication Pass
# Remove duplicates where both the title and author match an earlier entry.
# ------------------------------------------------------------------------------
print("-" * 60)
print("STEP 1: DE-DUPLICATION PASS")
print("-" * 60)

seen_books = set()
working_books = []
removed_books = []

for book in books:
    # Use (title, author) in lowercase as a unique identifier
    book_id = (book["title"].strip().lower(), book["author"].strip().lower())
    
    if book_id in seen_books:
        removed_books.append(book)
    else:
        seen_books.add(book_id)
        working_books.append(book)

# Print removal summary
if removed_books:
    print(f"Removed {len(removed_books)} duplicate record(s):")
    for removed in removed_books:
        print(f"  - Removed: '{removed['title']}' by {removed['author']}")
        print(f"    Reason: Duplicate title and author already present in inventory.")
else:
    print("No duplicate records found.")

print(f"\nWorking collection count after de-duplication: {len(working_books)}\n")

# ------------------------------------------------------------------------------
# STEP 2: Genre Report
# Calculate total titles, average price, and newest release for each genre.
# ------------------------------------------------------------------------------
print("-" * 60)
print("STEP 2: GENRE REPORT")
print("-" * 60)

# Get sorted list of unique genres
unique_genres = sorted({b["genre"] for b in working_books})

genre_report = {}
for genre in unique_genres:
    # Get all books for this genre
    genre_books = [b for b in working_books if b["genre"] == genre]
    
    total_titles = len(genre_books)
    avg_price = sum(b["price"] for b in genre_books) / total_titles
    newest_book = max(genre_books, key=lambda b: b["year"])["title"]
    
    genre_report[genre] = {
        "total_titles": total_titles,
        "average_price": avg_price,
        "most_recent_title": newest_book,
    }

# Display genre report
for genre, stats in genre_report.items():
    print(f"Genre: {genre}")
    print(f"  - Total Titles        : {stats['total_titles']}")
    print(f"  - Average Price       : ${stats['average_price']:.2f}")
    print(f"  - Most Recent Title   : {stats['most_recent_title']}")
    print()

# ------------------------------------------------------------------------------
# STEP 3: Author to Titles Mapping
# Group all book titles under their respective authors.
# ------------------------------------------------------------------------------
print("-" * 60)
print("STEP 3: AUTHOR TO TITLES MAPPING")
print("-" * 60)

author_to_titles = {}
for book in working_books:
    author = book["author"]
    title = book["title"]
    
    # If author is not yet in dictionary, start a new list
    if author not in author_to_titles:
        author_to_titles[author] = []
    author_to_titles[author].append(title)

# Display author mapping
for author, titles in author_to_titles.items():
    print(f"{author}:")
    for title in titles:
        print(f"  * {title}")
print()

# ------------------------------------------------------------------------------
# STEP 4: Author Analysis
# Identify total unique authors and authors with more than 1 book.
# ------------------------------------------------------------------------------
print("-" * 60)
print("STEP 4: AUTHOR ANALYSIS")
print("-" * 60)

# All unique authors sorted alphabetically
all_unique_authors = sorted(author_to_titles.keys())

# Authors with more than one book in stock
repeat_authors = [
    author for author, titles in author_to_titles.items() if len(titles) > 1
]

print(f"Total Unique Authors ({len(all_unique_authors)}):")
for author in all_unique_authors:
    print(f"  - {author}")

print(f"\nAuthors with More Than One Book in Stock ({len(repeat_authors)}):")
for author in sorted(repeat_authors):
    count = len(author_to_titles[author])
    print(f"  - {author} ({count} titles)")

print("\n" + "=" * 60)
print("ANALYSIS COMPLETE")
print("=" * 60)
