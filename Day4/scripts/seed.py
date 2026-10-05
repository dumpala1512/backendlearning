"""
================================================================================
Film Review Platform - Repeatable Developer Setup & Data Seeding Guide
================================================================================

This script provides an idempotent seed mechanism for populating baseline
development and testing data into the PostgreSQL database.

IMPORTANT ARCHITECTURAL DISTINCTION:
------------------------------------
- Database Schema Evolution is strictly managed via Alembic migrations.
  Schema changes must NEVER be performed via raw DDL or seed scripts.
- Data Seeding is an independent, application-level concern. Migrations should
  never contain volatile or environment-specific seed data.

COMPLETE DEVELOPER SETUP WORKFLOW:
----------------------------------
Follow these exact steps to onboard and initialize a fully working database:

1. Start the PostgreSQL database container (or ensure local PostgreSQL is running):
   $ docker compose up -d db

2. Apply all pending Alembic schema migrations:
   $ uv run alembic upgrade head
   (This creates the versioned schema: users, films, reviews, and watchlist tables,
    and records the revision in the alembic_version table.)

3. Run this idempotent seed script to populate initial baseline data:
   $ uv run python scripts/seed.py

4. Verify the database state:
   - Database is now fully migrated and populated with baseline users, films,
     and reviews.
   - You can re-run this seed script as many times as you like:
     running it 1 time or 10 times will always produce the exact same database state.

5. Start the FastAPI development server:
   $ uv run uvicorn app.main:app --reload --port 8000

================================================================================
"""
from __future__ import annotations

import asyncio
import logging
import sys
import uuid
from pathlib import Path

# Add project root to sys.path so scripts can be executed directly
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import select
from app.core.database import async_session_factory, engine
from app.models.film import Film
from app.models.review import Review
from app.models.user import User
from app.models.watchlist import Watchlist


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("seed")

# ==============================================================================
# Baseline Seed Data Definitions
# ==============================================================================

SEED_USERS = [
    {
        "username": "admin_sarah",
        "full_name": "Sarah Connor",
        "email": "sarah.admin@filmcritic.org",
        "role": "admin",
        "hashed_password": "pbkdf2_sha256$260000$admin_hashed_pw_seed_placeholder",
    },
    {
        "username": "marcus_reviews",
        "full_name": "Marcus Vance",
        "email": "marcus.critic@filmjournal.com",
        "role": "critic",
        "hashed_password": "pbkdf2_sha256$260000$critic_hashed_pw_seed_placeholder",
    },
    {
        "username": "elena_cinephile",
        "full_name": "Elena Rostova",
        "email": "elena.member@movielovers.net",
        "role": "member",
        "hashed_password": "pbkdf2_sha256$260000$member_hashed_pw_seed_placeholder",
    },
    {
        "username": "alex_viewer",
        "full_name": "Alex Mercer",
        "email": "alex.viewer@streamguide.io",
        "role": "user",
        "hashed_password": "pbkdf2_sha256$260000$user_hashed_pw_seed_placeholder",
    },
]

SEED_FILMS = [
    {
        "title": "Inception",
        "director": "Christopher Nolan",
        "release_year": 2010,
        "genre": "Sci-Fi",
        "description": "A thief who steals corporate secrets through dream-sharing technology is given the inverse task of planting an idea into the mind of a C.E.O.",
    },
    {
        "title": "The Dark Knight",
        "director": "Christopher Nolan",
        "release_year": 2008,
        "genre": "Action",
        "description": "When the menace known as the Joker wreaks havoc and chaos on the people of Gotham, Batman must accept one of the greatest psychological and physical tests.",
    },
    {
        "title": "Interstellar",
        "director": "Christopher Nolan",
        "release_year": 2014,
        "genre": "Sci-Fi",
        "description": "A team of explorers travel through a wormhole in space in an attempt to ensure humanity's survival as Earth faces catastrophic blight.",
    },
    {
        "title": "Parasite",
        "director": "Bong Joon-ho",
        "release_year": 2019,
        "genre": "Thriller",
        "description": "Greed and class discrimination threaten the newly formed symbiotic relationship between the wealthy Park family and the destitute Kim clan.",
    },
    {
        "title": "Spirited Away",
        "director": "Hayao Miyazaki",
        "release_year": 2001,
        "genre": "Animation",
        "description": "During her family's move to the suburbs, a sullen 10-year-old girl wanders into a world ruled by gods, witches, and spirits where humans are changed into beasts.",
    },
    {
        "title": "The Grand Budapest Hotel",
        "director": "Wes Anderson",
        "release_year": 2014,
        "genre": "Comedy",
        "description": "A writer encounters the owner of an aging high-class hotel, who tells him of his early years serving as a lobby boy in the glorious heyday under an eccentric concierge.",
    },
    {
        "title": "Whiplash",
        "director": "Damien Chazelle",
        "release_year": 2014,
        "genre": "Drama",
        "description": "A promising young drummer enrolls at a cut-throat music conservatory where his dreams of greatness are mentored by an instructor who will stop at nothing to realize a student's potential.",
    },
    {
        "title": "Blade Runner 2049",
        "director": "Denis Villeneuve",
        "release_year": 2017,
        "genre": "Sci-Fi",
        "description": "Young Blade Runner K's discovery of a long-buried secret leads him to track down former Blade Runner Rick Deckard, who's been missing for thirty years.",
    },
    {
        "title": "Knives Out",
        "director": "Rian Johnson",
        "release_year": 2019,
        "genre": "Comedy",
        "description": "A detective investigates the death of a patriarch of an eccentric, combative family in this clever modern murder-mystery whodunit.",
    },
    {
        "title": "Oppenheimer",
        "director": "Christopher Nolan",
        "release_year": 2023,
        "genre": "Drama",
        "description": "The story of American scientist J. Robert Oppenheimer and his role in the development of the atomic bomb during World War II.",
    },
    {
        "title": "Mad Max: Fury Road",
        "director": "George Miller",
        "release_year": 2015,
        "genre": "Action",
        "description": "In a post-apocalyptic wasteland, a woman rebels against a tyrannical ruler in search for her homeland with the aid of a group of female prisoners and a drifter named Max.",
    },
    {
        "title": "Pulp Fiction",
        "director": "Quentin Tarantino",
        "release_year": 1994,
        "genre": "Crime",
        "description": "The lives of two mob hitmen, a boxer, a gangster and his wife, and a pair of diner bandits intertwine in four tales of violence and redemption.",
    },
]

SEED_REVIEWS = [
    {
        "film_title": "Inception",
        "film_year": 2010,
        "username": "marcus_reviews",
        "reviewer_display_name": "Marcus Vance (Lead Critic)",
        "rating": 10,
        "review": "A masterclass in modern cinema combining high-concept cerebral sci-fi with relentless emotional momentum and groundbreaking visual effects.",
    },
    {
        "film_title": "The Dark Knight",
        "film_year": 2008,
        "username": "marcus_reviews",
        "reviewer_display_name": "Marcus Vance (Lead Critic)",
        "rating": 10,
        "review": "Heath Ledger's tour-de-force performance elevates this film beyond the comic book genre into an unforgettable crime epic and philosophical tragedy.",
    },
    {
        "film_title": "Parasite",
        "film_year": 2019,
        "username": "elena_cinephile",
        "reviewer_display_name": "Elena Rostova",
        "rating": 10,
        "review": "Brilliant and razor-sharp social satire that seamlessly pivots between pitch-black comedy and devastating architectural thriller without a wasted frame.",
    },
    {
        "film_title": "The Grand Budapest Hotel",
        "film_year": 2014,
        "username": "elena_cinephile",
        "reviewer_display_name": "Elena Rostova",
        "rating": 9,
        "review": "Meticulously framed, whimsical, and unexpectedly poignant. Ralph Fiennes gives one of his absolute finest comedic performances.",
    },
    {
        "film_title": "Whiplash",
        "film_year": 2014,
        "username": "alex_viewer",
        "reviewer_display_name": "Alex Mercer",
        "rating": 9,
        "review": "The most intense depiction of artistic ambition and psychological warfare since Black Swan. The final ten-minute drum solo is pure adrenaline.",
    },
    {
        "film_title": "Blade Runner 2049",
        "film_year": 2017,
        "username": "marcus_reviews",
        "reviewer_display_name": "Marcus Vance (Lead Critic)",
        "rating": 9,
        "review": "A rare sequel that honors and expands upon its legendary predecessor. Roger Deakins's cinematography and Zimmer's score create a monumental atmosphere.",
    },
    {
        "film_title": "Knives Out",
        "film_year": 2019,
        "username": "admin_sarah",
        "reviewer_display_name": "Sarah Connor (Admin)",
        "rating": 8,
        "review": "Delightfully entertaining with fantastic ensemble acting. Daniel Craig's southern drawl and Ana de Armas's grounded performance steal the entire show.",
    },
]

SEED_WATCHLIST = [
    {"username": "elena_cinephile", "film_title": "Inception", "film_year": 2010},
    {"username": "elena_cinephile", "film_title": "Interstellar", "film_year": 2014},
    {"username": "elena_cinephile", "film_title": "Blade Runner 2049", "film_year": 2017},
    {"username": "alex_viewer", "film_title": "The Dark Knight", "film_year": 2008},
    {"username": "alex_viewer", "film_title": "Mad Max: Fury Road", "film_year": 2015},
    {"username": "marcus_reviews", "film_title": "Oppenheimer", "film_year": 2023},
]


# ==============================================================================
# Idempotent Seeding Logic
# ==============================================================================

async def seed_users(session) -> dict[str, uuid.UUID]:
    """
    Idempotently seeds users. Checks existence by unique username.
    Returns mapping of username -> user.id.
    """
    logger.info("--- Seeding Users ---")
    user_map: dict[str, uuid.UUID] = {}
    created_count = 0
    existing_count = 0

    for user_data in SEED_USERS:
        stmt = select(User).where(User.username == user_data["username"])
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if user is None:
            user = User(
                username=user_data["username"],
                full_name=user_data["full_name"],
                email=user_data["email"],
                role=user_data["role"],
                hashed_password=user_data["hashed_password"],
            )
            session.add(user)
            await session.flush()
            created_count += 1
            logger.info(f"  [+] Created user: '{user.username}' (role={user.role})")
        else:
            # Update baseline attributes if needed
            user.full_name = user_data["full_name"]
            user.email = user_data["email"]
            user.role = user_data["role"]
            existing_count += 1
            logger.info(f"  [.] User already exists: '{user.username}' (id={user.id})")

        user_map[user.username] = user.id

    logger.info(f"Users summary: {created_count} created, {existing_count} already existed.")
    return user_map


async def seed_films(session) -> dict[tuple[str, int], uuid.UUID]:
    """
    Idempotently seeds films. Checks existence by (title, release_year).
    Returns mapping of (title, release_year) -> film.id.
    """
    logger.info("--- Seeding Films ---")
    film_map: dict[tuple[str, int], uuid.UUID] = {}
    created_count = 0
    existing_count = 0

    for film_data in SEED_FILMS:
        stmt = select(Film).where(
            Film.title == film_data["title"],
            Film.release_year == film_data["release_year"],
        )
        result = await session.execute(stmt)
        film = result.scalar_one_or_none()

        if film is None:
            film = Film(
                title=film_data["title"],
                director=film_data["director"],
                release_year=film_data["release_year"],
                genre=film_data["genre"],
                description=film_data["description"],
            )
            session.add(film)
            await session.flush()
            created_count += 1
            logger.info(
                f"  [+] Created film: '{film.title}' ({film.release_year}, {film.genre})"
            )
        else:
            # Refresh baseline attributes
            film.director = film_data["director"]
            film.genre = film_data["genre"]
            film.description = film_data["description"]
            existing_count += 1
            logger.info(f"  [.] Film already exists: '{film.title}' (id={film.id})")

        film_map[(film.title, film.release_year)] = film.id

    logger.info(f"Films summary: {created_count} created, {existing_count} already existed.")
    return film_map


async def seed_reviews(
    session,
    user_map: dict[str, uuid.UUID],
    film_map: dict[tuple[str, int], uuid.UUID],
) -> None:
    """
    Idempotently seeds reviews. Checks existence by (film_id, user_id).
    """
    logger.info("--- Seeding Reviews ---")
    created_count = 0
    existing_count = 0

    for rev_data in SEED_REVIEWS:
        title = str(rev_data["film_title"])
        year = int(rev_data["film_year"])
        username = str(rev_data["username"])
        film_id = film_map.get((title, year))
        user_id = user_map.get(username)

        if film_id is None or user_id is None:
            logger.warning(
                f"  [!] Skipping review: Could not resolve film '{title}' or user '{username}'"
            )
            continue

        stmt = select(Review).where(
            Review.film_id == film_id,
            Review.user_id == user_id,
        )
        result = await session.execute(stmt)
        review = result.scalar_one_or_none()

        if review is None:
            review = Review(
                film_id=film_id,
                user_id=user_id,
                rating=rev_data["rating"],
                review=rev_data["review"],
                reviewer_display_name=rev_data["reviewer_display_name"],
            )
            session.add(review)
            created_count += 1
            logger.info(
                f"  [+] Created review: user='{rev_data['username']}' -> film='{rev_data['film_title']}' (rating={rev_data['rating']}/10)"
            )
        else:
            # Refresh review content if appropriate
            review.rating = rev_data["rating"]
            review.review = rev_data["review"]
            review.reviewer_display_name = rev_data["reviewer_display_name"]
            existing_count += 1
            logger.info(
                f"  [.] Review already exists: user='{rev_data['username']}' -> film='{rev_data['film_title']}' (id={review.id})"
            )

    logger.info(f"Reviews summary: {created_count} created, {existing_count} already existed.")


async def seed_watchlist(
    session,
    user_map: dict[str, uuid.UUID],
    film_map: dict[tuple[str, int], uuid.UUID],
) -> None:
    """
    Idempotently seeds watchlist entries. Checks existence by composite PK (user_id, film_id).
    """
    logger.info("--- Seeding Watchlist ---")
    created_count = 0
    existing_count = 0

    for item in SEED_WATCHLIST:
        title = str(item["film_title"])
        year = int(item["film_year"])
        username = str(item["username"])
        film_id = film_map.get((title, year))
        user_id = user_map.get(username)

        if film_id is None or user_id is None:
            continue

        stmt = select(Watchlist).where(
            Watchlist.user_id == user_id,
            Watchlist.film_id == film_id,
        )
        result = await session.execute(stmt)
        entry = result.scalar_one_or_none()

        if entry is None:
            entry = Watchlist(user_id=user_id, film_id=film_id)
            session.add(entry)
            created_count += 1
            logger.info(f"  [+] Added to watchlist: user='{item['username']}' -> film='{item['film_title']}'")
        else:
            existing_count += 1
            logger.info(f"  [.] Watchlist item already exists: user='{item['username']}' -> film='{item['film_title']}'")

    logger.info(f"Watchlist summary: {created_count} created, {existing_count} already existed.")


async def main() -> None:
    """Main idempotent seeding routine wrapped in an async transaction."""
    logger.info("==================================================")
    logger.info("Starting idempotent database seeding...")
    logger.info("==================================================")

    async with async_session_factory() as session:
        async with session.begin():
            user_map = await seed_users(session)
            film_map = await seed_films(session)
            await seed_reviews(session, user_map, film_map)
            await seed_watchlist(session, user_map, film_map)

    await engine.dispose()
    logger.info("==================================================")
    logger.info("Database seeding finished successfully!")
    logger.info("==================================================")


if __name__ == "__main__":
    asyncio.run(main())
