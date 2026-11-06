from __future__ import annotations

import uuid
import pytest

from app.exceptions.film import FilmHasActiveReviewsError, FilmNotFoundError
from app.exceptions.review import (
    DuplicateReviewError,
    InvalidReviewRatingError,
    ReviewNotFoundError,
    UnauthorizedReviewDeleteError,
    UnauthorizedReviewUpdateError,
)
from app.models.film import Film
from app.models.user import User
from tests.fakes import FakeFilmRepository, FilmService, ReviewService


@pytest.mark.unit
def test_duplicate_review_exception_details(
    review_service: ReviewService,
    fake_film_repository: FakeFilmRepository,
    film: Film,
    viewer_user: User,
) -> None:
    """
    Verify DuplicateReviewError stores correct identifiers:
    - exception.film_id equals the film id
    - exception.user_id equals the user id
    - exception.review_id equals the original review id
    - exception message clearly describes the conflict
    """
    fake_film_repository.add(film)
    original = review_service.add_review(
        film_id=film.id,
        user_id=viewer_user.id,
        rating=8,
        review="First review submission.",
    )

    with pytest.raises(DuplicateReviewError) as exc_info:
        review_service.add_review(
            film_id=film.id,
            user_id=viewer_user.id,
            rating=9,
            review="Duplicate review attempt.",
        )

    exc = exc_info.value
    assert exc.film_id == film.id
    assert exc.user_id == viewer_user.id
    assert exc.review_id == original.id
    assert str(film.id) in exc.message
    assert str(viewer_user.id) in exc.message
    assert "already reviewed" in exc.message.lower()


@pytest.mark.unit
def test_review_not_found_exception_details(
    review_service: ReviewService,
) -> None:
    """
    Verify ReviewNotFoundError stores correct resource identifier:
    - exception.resource_id equals the review id
    - exception.review_id equals the review id
    - exception message clearly indicates the missing entity
    """
    missing_id = uuid.uuid4()

    with pytest.raises(ReviewNotFoundError) as exc_info:
        review_service.get_review(missing_id)

    exc = exc_info.value
    assert exc.resource_id == missing_id
    assert exc.review_id == missing_id
    assert str(missing_id) in exc.message
    assert "not found" in exc.message.lower()


@pytest.mark.unit
def test_unauthorized_review_update_exception_details(
    review_service: ReviewService,
    fake_film_repository: FakeFilmRepository,
    film: Film,
    viewer_user: User,
    other_viewer_user: User,
) -> None:
    """
    Verify UnauthorizedReviewUpdateError stores:
    - exception.resource_id equals the target review id
    - exception.user_id equals the unauthorized caller's user id
    - exception message specifies permission denial
    """
    fake_film_repository.add(film)
    original_review = review_service.add_review(
        film_id=film.id,
        user_id=viewer_user.id,
        rating=7,
        review="Original author review text.",
    )

    with pytest.raises(UnauthorizedReviewUpdateError) as exc_info:
        review_service.update_review(
            review_id=original_review.id,
            user_id=other_viewer_user.id,
            rating=1,
            review="Unauthorized modification attempt.",
        )

    exc = exc_info.value
    assert exc.resource_id == original_review.id
    assert exc.review_id == original_review.id
    assert exc.user_id == other_viewer_user.id
    assert "permission denied" in exc.message.lower()
    assert str(original_review.id) in exc.message


@pytest.mark.unit
def test_unauthorized_review_delete_exception_details(
    review_service: ReviewService,
    fake_film_repository: FakeFilmRepository,
    film: Film,
    viewer_user: User,
    other_viewer_user: User,
) -> None:
    """
    Verify UnauthorizedReviewDeleteError stores:
    - exception.resource_id equals the target review id
    - exception.user_id equals the unauthorized caller's user id
    """
    fake_film_repository.add(film)
    original_review = review_service.add_review(
        film_id=film.id,
        user_id=viewer_user.id,
        rating=7,
        review="Original review.",
    )

    with pytest.raises(UnauthorizedReviewDeleteError) as exc_info:
        review_service.delete_review(
            review_id=original_review.id,
            user_id=other_viewer_user.id,
        )

    exc = exc_info.value
    assert exc.resource_id == original_review.id
    assert exc.review_id == original_review.id
    assert exc.user_id == other_viewer_user.id
    assert "permission denied" in exc.message.lower()


@pytest.mark.unit
def test_film_not_found_exception_details(
    film_service: FilmService,
) -> None:
    """
    Verify FilmNotFoundError stores:
    - exception.resource_id equals the missing film id
    - exception.film_id equals the missing film id
    - exception message reflects the missing identifier
    """
    missing_id = uuid.uuid4()

    with pytest.raises(FilmNotFoundError) as exc_info:
        film_service.get_film(missing_id)

    exc = exc_info.value
    assert exc.resource_id == missing_id
    assert exc.film_id == missing_id
    assert str(missing_id) in exc.message
    assert "not found" in exc.message.lower()


@pytest.mark.unit
def test_film_has_active_reviews_exception_details(
    film_service: FilmService,
    review_service: ReviewService,
    film: Film,
    viewer_user: User,
    other_viewer_user: User,
) -> None:
    """
    Verify FilmHasActiveReviewsError stores:
    - exception.film_id equals the target film id
    - exception.active_reviews_count equals the number of active reviews
    - exception message notes active review constraint
    """
    film_service.repository.add(film)
    review_service.add_review(
        film_id=film.id,
        user_id=viewer_user.id,
        rating=8,
        review="First review.",
    )
    review_service.add_review(
        film_id=film.id,
        user_id=other_viewer_user.id,
        rating=9,
        review="Second review.",
    )

    with pytest.raises(FilmHasActiveReviewsError) as exc_info:
        film_service.delete_film(film.id)

    exc = exc_info.value
    assert exc.film_id == film.id
    assert exc.active_reviews_count == 2
    assert "cannot be deleted" in exc.message.lower()
    assert "2 active reviews" in exc.message.lower()


@pytest.mark.unit
def test_invalid_review_rating_exception_details(
    review_service: ReviewService,
    fake_film_repository: FakeFilmRepository,
    film: Film,
    viewer_user: User,
    valid_rating_range: tuple[int, int],
) -> None:
    """
    Verify InvalidReviewRatingError stores:
    - exception.rating equals the rejected rating value
    - exception.min_rating matches session-scoped valid_rating_range[0]
    - exception.max_rating matches session-scoped valid_rating_range[1]
    - exception message mentions the invalid rating value
    """
    min_rating, max_rating = valid_rating_range
    fake_film_repository.add(film)

    with pytest.raises(InvalidReviewRatingError) as exc_info:
        review_service.add_review(
            film_id=film.id,
            user_id=viewer_user.id,
            rating=15,
            review="Invalid rating.",
        )

    exc = exc_info.value
    assert exc.rating == 15
    assert exc.min_rating == min_rating
    assert exc.max_rating == max_rating
    assert "15" in exc.message
    assert "between 1 and 10" in exc.message.lower()
