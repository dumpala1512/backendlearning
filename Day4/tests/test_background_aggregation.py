from __future__ import annotations

import uuid
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dao.film_dao import FilmDAO
from app.dao.review_dao import ReviewDAO
from app.models.film import Film
from app.models.review import Review
from app.services.film_service import FilmService, recalculate_film_stats_task


@pytest.mark.database
async def test_background_aggregation_task_direct_invocation(
    db_session: AsyncSession,
) -> None:
    """
    Requirement 4: Background Aggregation Task Test.

    The application maintains review_count and average_rating using a background task.
    Do NOT mock the database.

    Flow:
    1. Create a film
    2. Insert multiple reviews into the test database with ratings [5, 4, 2]
    3. Call the aggregation task function directly
    4. Query the database afterwards

    Verify:
    - review_count updated correctly (= 3)
    - average_rating calculated correctly (= 3.67)
    - values persisted
    - Tested independently without requiring FastAPI BackgroundTasks.
    """
    film_dao = FilmDAO()
    review_dao = ReviewDAO()

    # Step 1: Create a film in the real test database
    film = await film_dao.create(
        session=db_session,
        title="Blade Runner 2049",
        director="Denis Villeneuve",
        release_year=2017,
        genre="Sci-Fi",
        description="A young blade runner unearths a long-buried secret that leads him to former blade runner Rick Deckard.",
    )
    film_id = film.id
    assert film.total_reviews == 0
    assert film.average_rating is None

    # Step 2: Insert multiple reviews with exact example ratings from prompt: [5, 4, 2]
    ratings = [5, 4, 2]
    for idx, rating_val in enumerate(ratings, start=1):
        await review_dao.create(
            session=db_session,
            film_id=film_id,
            rating=rating_val,
            review=f"Review number {idx} with rating {rating_val} for testing background aggregation.",
            reviewer_display_name=f"Critic {idx}",
        )

    # Step 3: Call the aggregation task function directly without FastAPI BackgroundTasks
    updated = await recalculate_film_stats_task(film_id=film_id, session=db_session)
    assert updated is not None

    # Step 4: Query the database directly afterwards to verify persistence
    result = await db_session.execute(select(Film).where(Film.id == film_id))
    persisted_film = result.scalar_one()

    # Verify review_count / total_reviews
    assert persisted_film.total_reviews == 3
    assert persisted_film.review_count == 3

    # Verify average_rating is 3.67 (5 + 4 + 2 = 11 / 3 = 3.6666... -> 3.67)
    assert persisted_film.average_rating == 3.67
    assert persisted_film.average_rating == pytest.approx(3.67, rel=1e-3)


@pytest.mark.database
async def test_background_aggregation_zero_reviews_reset(
    db_session: AsyncSession,
) -> None:
    """
    Requirement 4 & 10: Test background aggregation on a film with zero reviews.
    Verifies that total_reviews is 0 and average_rating resets to None.
    """
    film_dao = FilmDAO()
    review_dao = ReviewDAO()

    # Create film with initial non-zero stats
    film = await film_dao.create(
        session=db_session,
        title="Unrated Indie Film",
        director="Unknown Artist",
        release_year=2024,
        genre="Drama",
    )
    # Manually set stats to simulate prior reviews that have all been removed
    await film_dao.update(
        session=db_session,
        film_id=film.id,
        total_reviews=2,
        average_rating=7.5,
    )

    # Invoke aggregation task directly
    service = FilmService(dao=film_dao, review_dao=review_dao)
    await service.recalculate_film_stats(session=db_session, film_id=film.id)

    # Query directly from database
    result = await db_session.execute(select(Film).where(Film.id == film.id))
    db_film = result.scalar_one()

    assert db_film.total_reviews == 0
    assert db_film.review_count == 0
    assert db_film.average_rating is None


@pytest.mark.database
async def test_background_aggregation_non_existent_film(
    db_session: AsyncSession,
) -> None:
    """
    Verify recalculate_film_stats returns None gracefully when film does not exist.
    """
    film_dao = FilmDAO()
    review_dao = ReviewDAO()
    service = FilmService(dao=film_dao, review_dao=review_dao)

    non_existent_id = uuid.uuid4()
    result = await service.recalculate_film_stats(session=db_session, film_id=non_existent_id)
    assert result is None
