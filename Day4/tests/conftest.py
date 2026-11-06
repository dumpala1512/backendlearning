from __future__ import annotations

from datetime import datetime, timezone
import uuid

import pytest

from app.models.film import Film
from app.models.review import Review
from app.models.user import User
from tests.fakes import (
    FakeFilmRepository,
    FakeRepository,
    FakeReviewRepository,
    FilmService,
    ReviewService,
)
from tests.fixtures import (
    app,
    async_engine,
    client,
    db_connection,
    db_session,
    fake_redis,
)



# ---------------------------------------------------------------------------
# Session & Module Scoped Fixtures (Immutable shared data)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def valid_rating_range() -> tuple[int, int]:
    """Session-scoped immutable specification of minimum and maximum allowed ratings."""
    return (1, 10)


@pytest.fixture(scope="module")
def immutable_genres() -> tuple[str, ...]:
    """Module-scoped immutable tuple of standard film genres."""
    return ("Action", "Sci-Fi", "Crime", "Animation", "Drama", "Comedy", "Horror")


# ---------------------------------------------------------------------------
# Function Scoped User Fixtures (Fresh mutable domain entities)
# ---------------------------------------------------------------------------

@pytest.fixture
def admin_user() -> User:
    """Fixture providing a user with admin privileges."""
    return User(
        id=uuid.uuid4(),
        username="sarah_admin",
        full_name="Sarah Connor",
        email="sarah.admin@example.com",
        role="admin",
        hashed_password="hashed_admin_pass",
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def critic_user() -> User:
    """Fixture providing a certified critic user."""
    return User(
        id=uuid.uuid4(),
        username="ebert_critic",
        full_name="Roger Ebert",
        email="roger.critic@example.com",
        role="critic",
        hashed_password="hashed_critic_pass",
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def viewer_user() -> User:
    """Fixture providing a standard viewer user."""
    return User(
        id=uuid.uuid4(),
        username="alex_viewer",
        full_name="Alex Turner",
        email="alex.viewer@example.com",
        role="viewer",
        hashed_password="hashed_viewer_pass",
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def other_viewer_user() -> User:
    """Fixture providing a secondary viewer user for multi-user tests."""
    return User(
        id=uuid.uuid4(),
        username="bob_viewer",
        full_name="Bob Stone",
        email="bob.viewer@example.com",
        role="viewer",
        hashed_password="hashed_viewer_pass",
        created_at=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# Function Scoped Film Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def film() -> Film:
    """Fixture providing a single representative Film domain model."""
    return Film(
        id=uuid.uuid4(),
        title="Inception",
        director="Christopher Nolan",
        release_year=2010,
        genre="Sci-Fi",
        description="A skilled thief steals corporate secrets through dream-sharing technology.",
        is_active=True,
        total_reviews=0,
        average_rating=None,
    )


@pytest.fixture
def multiple_films() -> list[Film]:
    """Fixture providing a diverse collection of films for filtering and querying."""
    return [
        Film(
            id=uuid.uuid4(),
            title="Inception",
            director="Christopher Nolan",
            release_year=2010,
            genre="Sci-Fi",
            description="Dream infiltration and espionage.",
            is_active=True,
            total_reviews=0,
            average_rating=None,
        ),
        Film(
            id=uuid.uuid4(),
            title="Interstellar",
            director="Christopher Nolan",
            release_year=2014,
            genre="Sci-Fi",
            description="Space expedition through a wormhole.",
            is_active=True,
            total_reviews=0,
            average_rating=None,
        ),
        Film(
            id=uuid.uuid4(),
            title="The Dark Knight",
            director="Christopher Nolan",
            release_year=2008,
            genre="Action",
            description="Batman faces the Joker in Gotham City.",
            is_active=True,
            total_reviews=0,
            average_rating=None,
        ),
        Film(
            id=uuid.uuid4(),
            title="Pulp Fiction",
            director="Quentin Tarantino",
            release_year=1994,
            genre="Crime",
            description="Intertwined crime stories in Los Angeles.",
            is_active=True,
            total_reviews=0,
            average_rating=None,
        ),
        Film(
            id=uuid.uuid4(),
            title="The Godfather",
            director="Francis Ford Coppola",
            release_year=1972,
            genre="Crime",
            description="Chronicle of an Italian-American crime family.",
            is_active=True,
            total_reviews=0,
            average_rating=None,
        ),
        Film(
            id=uuid.uuid4(),
            title="Spirited Away",
            director="Hayao Miyazaki",
            release_year=2001,
            genre="Animation",
            description="A young girl wanders into a magical world of spirits.",
            is_active=True,
            total_reviews=0,
            average_rating=None,
        ),
        Film(
            id=uuid.uuid4(),
            title="Parasite",
            director="Bong Joon-ho",
            release_year=2019,
            genre="Drama",
            description="A poor family infiltrates a wealthy household.",
            is_active=True,
            total_reviews=0,
            average_rating=None,
        ),
    ]


# ---------------------------------------------------------------------------
# Function Scoped Review Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def review(film: Film, viewer_user: User) -> Review:
    """Fixture providing a single review linked to a film and viewer."""
    return Review(
        id=uuid.uuid4(),
        film_id=film.id,
        user_id=viewer_user.id,
        rating=9,
        review="Exceptional storytelling with outstanding visual effects.",
        reviewer_display_name=viewer_user.username,
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def review_collection(film: Film, critic_user: User, viewer_user: User, other_viewer_user: User) -> list[Review]:
    """Fixture providing multiple reviews for the same film by different users."""
    return [
        Review(
            id=uuid.uuid4(),
            film_id=film.id,
            user_id=critic_user.id,
            rating=9,
            review="A masterpiece of modern cinema.",
            reviewer_display_name=critic_user.username,
            created_at=datetime.now(timezone.utc),
        ),
        Review(
            id=uuid.uuid4(),
            film_id=film.id,
            user_id=viewer_user.id,
            rating=8,
            review="Great movie, mind bending concept.",
            reviewer_display_name=viewer_user.username,
            created_at=datetime.now(timezone.utc),
        ),
        Review(
            id=uuid.uuid4(),
            film_id=film.id,
            user_id=other_viewer_user.id,
            rating=10,
            review="One of the best films ever made.",
            reviewer_display_name=other_viewer_user.username,
            created_at=datetime.now(timezone.utc),
        ),
    ]


# ---------------------------------------------------------------------------
# Function Scoped Repository and Service Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def fake_film_repository() -> FakeFilmRepository:
    """Fixture providing an isolated in-memory Film repository."""
    return FakeFilmRepository()


@pytest.fixture
def fake_review_repository() -> FakeReviewRepository:
    """Fixture providing an isolated in-memory Review repository."""
    return FakeReviewRepository()


@pytest.fixture
def fake_repository(
    fake_film_repository: FakeFilmRepository,
    fake_review_repository: FakeReviewRepository,
) -> FakeRepository:
    """Fixture providing a combined in-memory repository."""
    return FakeRepository(films=fake_film_repository, reviews=fake_review_repository)


@pytest.fixture
def film_service(
    fake_film_repository: FakeFilmRepository,
    fake_review_repository: FakeReviewRepository,
) -> FilmService:
    """Fixture providing a FilmService configured with isolated repositories."""
    return FilmService(
        repository=fake_film_repository,
        review_repository=fake_review_repository,
    )


@pytest.fixture
def review_service(
    fake_film_repository: FakeFilmRepository,
    fake_review_repository: FakeReviewRepository,
) -> ReviewService:
    """Fixture providing a ReviewService configured with isolated repositories."""
    return ReviewService(
        repository=fake_review_repository,
        film_repository=fake_film_repository,
    )
