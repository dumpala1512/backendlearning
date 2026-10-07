from __future__ import annotations

import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import DuplicateEntityError, FilmNotFoundError, ReviewNotFoundError
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


@pytest.mark.asyncio
async def test_rule_1_user_can_submit_only_one_review_per_film(db_session: AsyncSession):
    """Domain Rule 1: A user may submit only one review per film."""
    film_dao = FilmDAO()
    review_dao = ReviewDAO()
    user_dao = UserDAO()
    film_service = FilmService(dao=film_dao, review_dao=review_dao)
    review_service = ReviewService(dao=review_dao, film_dao=film_dao)
    user_service = UserService(dao=user_dao, film_dao=film_dao, review_dao=review_dao)

    user = await user_service.register(
        session=db_session,
        username="reviewer_one",
        full_name="Reviewer One",
        email="rev1@example.com",
        password="password123",
    )
    film = await film_service.create_film(
        session=db_session,
        title="Inception",
        director="Christopher Nolan",
        release_year=2010,
        genre="Sci-Fi",
    )

    # First review succeeds
    first_review = await review_service.add_review(
        session=db_session,
        film_id=film.id,
        user_id=user.id,
        rating=9,
        review="Mind-bending cinematic journey with extraordinary practical effects and score.",
        reviewer_display_name="Reviewer One",
    )
    assert first_review.id is not None

    # Second review for the same film by the same user raises ReviewAlreadyExistsError
    from app.exceptions.review import ReviewAlreadyExistsError

    with pytest.raises(ReviewAlreadyExistsError) as exc_info:
        await review_service.add_review(
            session=db_session,
            film_id=film.id,
            user_id=user.id,
            rating=10,
            review="Trying to post a second review for the same film should be blocked.",
            reviewer_display_name="Reviewer One Again",
        )

    err = exc_info.value
    assert err.film_id == film.id
    assert err.user_id == user.id
    assert err.error_type == "ReviewAlreadyExists"
    assert "already reviewed" in err.message.lower()


@pytest.mark.asyncio
async def test_rule_2_only_author_may_update_review(db_session: AsyncSession):
    """Domain Rule 2: Only the original author may update review rating and review body."""
    film_dao = FilmDAO()
    review_dao = ReviewDAO()
    user_dao = UserDAO()
    film_service = FilmService(dao=film_dao, review_dao=review_dao)
    review_service = ReviewService(dao=review_dao, film_dao=film_dao)
    user_service = UserService(dao=user_dao, film_dao=film_dao, review_dao=review_dao)

    author = await user_service.register(
        session=db_session,
        username="author_user",
        full_name="Author User",
        email="author@example.com",
        password="password123",
    )
    other_user = await user_service.register(
        session=db_session,
        username="other_user",
        full_name="Other User",
        email="other@example.com",
        password="password123",
    )
    film = await film_service.create_film(
        session=db_session,
        title="Interstellar",
        director="Christopher Nolan",
        release_year=2014,
        genre="Sci-Fi",
    )

    review = await review_service.add_review(
        session=db_session,
        film_id=film.id,
        user_id=author.id,
        rating=8,
        review="Visually stunning emotional space exploration odyssey that touches the heart.",
        reviewer_display_name="Author",
    )

    # Unauthorized user update raises ReviewPermissionDeniedError
    from app.exceptions.review import ReviewPermissionDeniedError

    with pytest.raises(ReviewPermissionDeniedError) as exc_info:
        await review_service.update_review(
            session=db_session,
            review_id=review.id,
            user_id=other_user.id,
            rating=2,
            review="Hacked and modified by unauthorized user!",
        )

    err = exc_info.value
    assert err.review_id == review.id
    assert err.user_id == other_user.id
    assert err.error_type == "ReviewPermissionDenied"

    # Original author update succeeds
    updated = await review_service.update_review(
        session=db_session,
        review_id=review.id,
        user_id=author.id,
        rating=10,
        review="Updated rating after rewatching the film in 70mm IMAX format.",
    )
    assert updated.rating == 10
    assert "70mm" in updated.review


@pytest.mark.asyncio
async def test_rule_3_film_cannot_be_soft_deleted_with_active_reviews(db_session: AsyncSession):
    """Domain Rule 3: A film may not be soft deleted while it still has active reviews."""
    film_dao = FilmDAO()
    review_dao = ReviewDAO()
    film_service = FilmService(dao=film_dao, review_dao=review_dao)
    review_service = ReviewService(dao=review_dao, film_dao=film_dao)

    film = await film_service.create_film(
        session=db_session,
        title="The Dark Knight",
        director="Christopher Nolan",
        release_year=2008,
        genre="Action",
    )
    review = await review_service.add_review(
        session=db_session,
        film_id=film.id,
        rating=10,
        review="Unforgettable performance by Heath Ledger as the Joker in Gotham City.",
    )

    # Attempting to delete film with active reviews raises FilmHasActiveReviewsError
    from app.exceptions.film import FilmHasActiveReviewsError

    with pytest.raises(FilmHasActiveReviewsError) as exc_info:
        await film_service.delete_film(session=db_session, film_id=film.id)

    err = exc_info.value
    assert err.film_id == film.id
    assert err.active_reviews_count == 1
    assert err.error_type == "FilmHasActiveReviews"

    # Once the active review is deleted, the film can be soft-deleted
    await review_service.delete_review(session=db_session, review_id=review.id)
    deleted = await film_service.delete_film(session=db_session, film_id=film.id)
    assert deleted is True

    # Film is now soft deleted (not found)
    from app.exceptions.film import FilmNotFoundError
    with pytest.raises(FilmNotFoundError):
        await film_service.get_by_id(session=db_session, film_id=film.id)
