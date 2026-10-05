from __future__ import annotations

import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DuplicateEntityError, FilmNotFoundError, ReviewNotFoundError
from app.dao.film_dao import FilmDAO
from app.dao.review_dao import ReviewDAO
from app.dao.user_dao import UserDAO
from app.services.film_service import FilmService
from app.services.review_service import ReviewService
from app.services.user_service import UserService


@pytest.mark.asyncio
async def test_film_service_raises_domain_exception(db_session: AsyncSession):
    film_dao = FilmDAO()
    film_service = FilmService(dao=film_dao)

    # Missing film should raise domain FilmNotFoundError (not an HTTP exception)
    with pytest.raises(FilmNotFoundError) as exc_info:
        await film_service.get_by_id(session=db_session, film_id=uuid.uuid4())
    assert "not found" in str(exc_info.value).lower()

    # Create film through service
    created = await film_service.create_film(
        session=db_session,
        title="Memento",
        director="Christopher Nolan",
        release_year=2000,
        genre="Mystery",
    )
    assert isinstance(created.id, uuid.UUID)
    assert created.title == "Memento"

    # Fetch existing
    fetched = await film_service.get_by_id(session=db_session, film_id=created.id)
    assert fetched.id == created.id

    # Update existing
    updated = await film_service.update_film(
        session=db_session,
        film_id=created.id,
        description="Non-linear storyline masterpiece.",
    )
    assert updated.description == "Non-linear storyline masterpiece."

    # Update non-existent raises FilmNotFoundError
    with pytest.raises(FilmNotFoundError):
        await film_service.update_film(session=db_session, film_id=uuid.uuid4(), description="test")

    # Delete existing
    deleted = await film_service.delete_film(session=db_session, film_id=created.id)
    assert deleted is True

    # Delete non-existent raises FilmNotFoundError
    with pytest.raises(FilmNotFoundError):
        await film_service.delete_film(session=db_session, film_id=uuid.uuid4())


@pytest.mark.asyncio
async def test_review_service_validation_and_exceptions(db_session: AsyncSession):
    film_dao = FilmDAO()
    review_dao = ReviewDAO()
    review_service = ReviewService(dao=review_dao, film_dao=film_dao)

    # Adding review for non-existent film raises FilmNotFoundError
    with pytest.raises(FilmNotFoundError):
        await review_service.add_review(
            session=db_session,
            film_id=uuid.uuid4(),
            rating=8,
            review="Great film, but doesn't exist!",
        )

    # Create film first
    film = await film_dao.create(
        session=db_session,
        title="Pulp Fiction",
        director="Quentin Tarantino",
        release_year=1994,
        genre="Crime",
    )

    # Add review
    review = await review_service.add_review(
        session=db_session,
        film_id=film.id,
        rating=10,
        review="Iconic cinematic dialogue and editing.",
        reviewer_display_name="MovieBuff",
    )
    assert isinstance(review.id, uuid.UUID)

    # Listing reviews
    reviews = await review_service.list_reviews(session=db_session, film_id=film.id)
    assert len(reviews) == 1

    # Average rating
    avg = await review_service.average_rating(session=db_session, film_id=film.id)
    assert avg == 10.0

    # Delete review
    assert await review_service.delete_review(session=db_session, review_id=review.id) is True

    # Delete non-existent review raises ReviewNotFoundError
    with pytest.raises(ReviewNotFoundError):
        await review_service.delete_review(session=db_session, review_id=uuid.uuid4())


@pytest.mark.asyncio
async def test_user_service_registration_and_duplicates(db_session: AsyncSession):
    user_dao = UserDAO()
    film_dao = FilmDAO()
    review_dao = ReviewDAO()
    user_service = UserService(dao=user_dao, film_dao=film_dao, review_dao=review_dao)

    # Register user with full_name
    user = await user_service.register(
        session=db_session,
        username="unique_user",
        full_name="Unique User Name",
        email="unique@domain.com",
        password="secure_password_123",
    )
    assert isinstance(user.id, uuid.UUID)
    assert user.full_name == "Unique User Name"

    # Duplicate username raises DuplicateEntityError
    with pytest.raises(DuplicateEntityError) as exc_info:
        await user_service.register(
            session=db_session,
            username="unique_user",
            full_name="Duplicate Username User",
            email="another@domain.com",
            password="secure_password_123",
        )
    assert "already taken" in str(exc_info.value).lower()

    # Duplicate email raises DuplicateEntityError
    with pytest.raises(DuplicateEntityError) as exc_info:
        await user_service.register(
            session=db_session,
            username="another_user",
            full_name="Duplicate Email User",
            email="unique@domain.com",
            password="secure_password_123",
        )
    assert "already registered" in str(exc_info.value).lower()
