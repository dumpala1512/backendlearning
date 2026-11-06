from __future__ import annotations

import uuid
import pytest

from app.exceptions.film import FilmHasActiveReviewsError, FilmNotFoundError
from app.models.film import Film
from app.models.user import User
from tests.fakes import FilmService, ReviewService


@pytest.mark.unit
def test_create_film_success(film_service: FilmService) -> None:
    """Test creating a new film validates fields and persists in-memory."""
    created = film_service.create_film(
        title="Oppenheimer",
        director="Christopher Nolan",
        release_year=2023,
        genre="Drama",
        description="The story of American scientist J. Robert Oppenheimer.",
    )

    assert created.id is not None
    assert isinstance(created.id, uuid.UUID)
    assert created.title == "Oppenheimer"
    assert created.director == "Christopher Nolan"
    assert created.release_year == 2023
    assert created.genre == "Drama"
    assert created.is_active is True
    assert created.total_reviews == 0
    assert created.average_rating is None


@pytest.mark.unit
def test_create_film_empty_title_raises_value_error(film_service: FilmService) -> None:
    """Test that creating a film with an empty or whitespace title raises ValueError."""
    with pytest.raises(ValueError) as exc_info:
        film_service.create_film(
            title="   ",
            director="Some Director",
            release_year=2020,
            genre="Action",
        )
    assert "title cannot be empty" in str(exc_info.value).lower()


@pytest.mark.unit
def test_get_film_by_id_success(film_service: FilmService, film: Film) -> None:
    """Test retrieving an existing active film by its UUID."""
    film_service.repository.add(film)

    retrieved = film_service.get_film(film.id)

    assert retrieved.id == film.id
    assert retrieved.title == film.title
    assert retrieved.director == film.director
    assert retrieved.release_year == film.release_year


@pytest.mark.unit
def test_get_nonexistent_film_raises_film_not_found_error(
    film_service: FilmService,
) -> None:
    """Test that requesting a missing film raises FilmNotFoundError with resource_id."""
    missing_id = uuid.uuid4()

    with pytest.raises(FilmNotFoundError) as exc_info:
        film_service.get_film(missing_id)

    assert exc_info.value.film_id == missing_id
    assert exc_info.value.resource_id == missing_id


@pytest.mark.unit
def test_update_film_success(film_service: FilmService, film: Film) -> None:
    """Test updating existing film attributes modifies stored values."""
    film_service.repository.add(film)

    updated = film_service.update_film(
        film.id,
        title="Inception: Special Edition",
        description="Updated extended description.",
    )

    assert updated.id == film.id
    assert updated.title == "Inception: Special Edition"
    assert updated.description == "Updated extended description."
    # Ensure director and year were unaffected
    assert updated.director == "Christopher Nolan"
    assert updated.release_year == 2010


@pytest.mark.unit
def test_update_nonexistent_film_raises_film_not_found_error(
    film_service: FilmService,
) -> None:
    """Test that updating a non-existent film raises FilmNotFoundError."""
    missing_id = uuid.uuid4()

    with pytest.raises(FilmNotFoundError) as exc_info:
        film_service.update_film(missing_id, title="Ghost Film")

    assert exc_info.value.film_id == missing_id


@pytest.mark.unit
def test_delete_film_without_reviews_succeeds(
    film_service: FilmService,
    film: Film,
) -> None:
    """Test deleting a film with no reviews succeeds and marks it inactive."""
    film_service.repository.add(film)

    deleted = film_service.delete_film(film.id)

    assert deleted is True
    # Attempting to fetch the deleted film now raises FilmNotFoundError
    with pytest.raises(FilmNotFoundError):
        film_service.get_film(film.id)


@pytest.mark.unit
def test_delete_nonexistent_film_raises_film_not_found_error(
    film_service: FilmService,
) -> None:
    """Test deleting a non-existent film raises FilmNotFoundError."""
    missing_id = uuid.uuid4()

    with pytest.raises(FilmNotFoundError) as exc_info:
        film_service.delete_film(missing_id)

    assert exc_info.value.film_id == missing_id


@pytest.mark.unit
def test_delete_film_with_active_reviews_raises_error(
    film_service: FilmService,
    review_service: ReviewService,
    film: Film,
    viewer_user: User,
) -> None:
    """Domain Rule 3: A film cannot be deleted while it still has active reviews."""
    film_service.repository.add(film)
    review_service.add_review(
        film_id=film.id,
        user_id=viewer_user.id,
        rating=9,
        review="Brilliant visionary film.",
    )

    with pytest.raises(FilmHasActiveReviewsError) as exc_info:
        film_service.delete_film(film.id)

    assert exc_info.value.film_id == film.id
    assert exc_info.value.active_reviews_count == 1
    assert "cannot be deleted" in str(exc_info.value).lower()


@pytest.mark.unit
def test_delete_film_succeeds_after_reviews_are_removed(
    film_service: FilmService,
    review_service: ReviewService,
    film: Film,
    viewer_user: User,
) -> None:
    """Test that a film can be safely deleted once all its reviews have been deleted."""
    film_service.repository.add(film)
    review = review_service.add_review(
        film_id=film.id,
        user_id=viewer_user.id,
        rating=8,
        review="Great cinematography.",
    )

    # Delete the active review
    deleted_review = review_service.delete_review(
        review_id=review.id,
        user_id=viewer_user.id,
    )
    assert deleted_review is True

    # Now film deletion succeeds
    deleted_film = film_service.delete_film(film.id)
    assert deleted_film is True


@pytest.mark.unit
def test_calculate_average_rating_without_reviews(
    film_service: FilmService,
    film: Film,
) -> None:
    """Test that a film with zero reviews returns None for average rating."""
    film_service.repository.add(film)

    avg = film_service.calculate_average_rating(film.id)
    assert avg is None
