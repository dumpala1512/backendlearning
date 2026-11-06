from __future__ import annotations

import uuid
import pytest

from app.exceptions.film import FilmNotFoundError
from app.exceptions.review import (
    DuplicateReviewError,
    InvalidReviewRatingError,
    ReviewNotFoundError,
    UnauthorizedReviewDeleteError,
    UnauthorizedReviewUpdateError,
)
from app.models.film import Film
from app.models.user import User
from tests.fakes import FakeFilmRepository, ReviewService


@pytest.mark.unit
def test_user_cannot_review_same_film_twice(
    review_service: ReviewService,
    fake_film_repository: FakeFilmRepository,
    film: Film,
    viewer_user: User,
) -> None:
    """Domain Rule 1: A user may submit only one review per film."""
    fake_film_repository.add(film)

    # First review succeeds
    first_review = review_service.add_review(
        film_id=film.id,
        user_id=viewer_user.id,
        rating=9,
        review="First impression: stunning visuals and sound design.",
        reviewer_display_name=viewer_user.username,
    )
    assert first_review.id is not None

    # Second review by the same user for the same film raises DuplicateReviewError
    with pytest.raises(DuplicateReviewError) as exc_info:
        review_service.add_review(
            film_id=film.id,
            user_id=viewer_user.id,
            rating=10,
            review="Attempting to post duplicate review.",
            reviewer_display_name=viewer_user.username,
        )

    err = exc_info.value
    assert err.film_id == film.id
    assert err.user_id == viewer_user.id
    assert err.review_id == first_review.id
    assert "already reviewed" in str(err).lower()


@pytest.mark.unit
def test_review_creation_on_nonexistent_film_raises_not_found(
    review_service: ReviewService,
    viewer_user: User,
) -> None:
    """Test adding a review to a non-existent film raises FilmNotFoundError."""
    missing_film_id = uuid.uuid4()

    with pytest.raises(FilmNotFoundError) as exc_info:
        review_service.add_review(
            film_id=missing_film_id,
            user_id=viewer_user.id,
            rating=8,
            review="Nice movie.",
        )

    assert exc_info.value.film_id == missing_film_id
    assert exc_info.value.resource_id == missing_film_id


@pytest.mark.unit
def test_review_ratings_must_stay_within_allowed_limits(
    review_service: ReviewService,
    fake_film_repository: FakeFilmRepository,
    film: Film,
    viewer_user: User,
    valid_rating_range: tuple[int, int],
) -> None:
    """Test that rating below 1 or above 10 raises InvalidReviewRatingError."""
    min_rating, max_rating = valid_rating_range
    fake_film_repository.add(film)

    # Below minimum
    with pytest.raises(InvalidReviewRatingError) as exc_low:
        review_service.add_review(
            film_id=film.id,
            user_id=viewer_user.id,
            rating=0,
            review="Too low score",
        )
    assert exc_low.value.rating == 0
    assert exc_low.value.min_rating == min_rating
    assert exc_low.value.max_rating == max_rating

    # Above maximum
    with pytest.raises(InvalidReviewRatingError) as exc_high:
        review_service.add_review(
            film_id=film.id,
            user_id=viewer_user.id,
            rating=11,
            review="Too high score",
        )
    assert exc_high.value.rating == 11
    assert exc_high.value.min_rating == min_rating
    assert exc_high.value.max_rating == max_rating


@pytest.mark.unit
def test_updating_review_changes_stored_values(
    review_service: ReviewService,
    fake_film_repository: FakeFilmRepository,
    film: Film,
    viewer_user: User,
) -> None:
    """Test updating a review changes both rating and body content in storage."""
    fake_film_repository.add(film)
    created = review_service.add_review(
        film_id=film.id,
        user_id=viewer_user.id,
        rating=7,
        review="Initial thoughts: decent watch.",
    )

    updated = review_service.update_review(
        review_id=created.id,
        user_id=viewer_user.id,
        rating=9,
        review="Second watch in IMAX changed my mind: exceptional film!",
    )

    assert updated.id == created.id
    assert updated.rating == 9
    assert updated.review == "Second watch in IMAX changed my mind: exceptional film!"

    # Verify retrieval returns modified entity
    retrieved = review_service.get_review(created.id)
    assert retrieved.rating == 9
    assert retrieved.review == "Second watch in IMAX changed my mind: exceptional film!"


@pytest.mark.unit
def test_only_original_author_may_edit_review(
    review_service: ReviewService,
    fake_film_repository: FakeFilmRepository,
    film: Film,
    viewer_user: User,
    other_viewer_user: User,
) -> None:
    """Domain Rule 2: Only the original author may edit a review."""
    fake_film_repository.add(film)
    review = review_service.add_review(
        film_id=film.id,
        user_id=viewer_user.id,
        rating=8,
        review="Original review text.",
    )

    # Another user attempts to update the review
    with pytest.raises(UnauthorizedReviewUpdateError) as exc_info:
        review_service.update_review(
            review_id=review.id,
            user_id=other_viewer_user.id,
            rating=3,
            review="Malicious overwrite by non-author.",
        )

    err = exc_info.value
    assert err.review_id == review.id
    assert err.resource_id == review.id
    assert err.user_id == other_viewer_user.id


@pytest.mark.unit
def test_admin_can_edit_any_review(
    review_service: ReviewService,
    fake_film_repository: FakeFilmRepository,
    film: Film,
    viewer_user: User,
    admin_user: User,
) -> None:
    """Test administrator with is_admin=True can moderate/update any review."""
    fake_film_repository.add(film)
    review = review_service.add_review(
        film_id=film.id,
        user_id=viewer_user.id,
        rating=6,
        review="Original review text.",
    )

    moderated = review_service.update_review(
        review_id=review.id,
        user_id=admin_user.id,
        is_admin=True,
        review="[Moderated: Content revised according to community standards]",
    )

    assert moderated.review == "[Moderated: Content revised according to community standards]"
    assert moderated.rating == 6


@pytest.mark.unit
def test_deleting_review_removes_it_from_collection(
    review_service: ReviewService,
    fake_film_repository: FakeFilmRepository,
    film: Film,
    viewer_user: User,
) -> None:
    """Test deleting a review removes it from in-memory collection."""
    fake_film_repository.add(film)
    review = review_service.add_review(
        film_id=film.id,
        user_id=viewer_user.id,
        rating=8,
        review="Temporary review.",
    )

    deleted = review_service.delete_review(
        review_id=review.id,
        user_id=viewer_user.id,
    )
    assert deleted is True

    # Review is no longer found
    with pytest.raises(ReviewNotFoundError) as exc_info:
        review_service.get_review(review.id)
    assert exc_info.value.resource_id == review.id

    # Review list for film is now empty
    reviews = review_service.list_reviews_for_film(film.id)
    assert len(reviews) == 0


@pytest.mark.unit
def test_only_original_author_may_delete_review(
    review_service: ReviewService,
    fake_film_repository: FakeFilmRepository,
    film: Film,
    viewer_user: User,
    other_viewer_user: User,
) -> None:
    """Test unauthorized user cannot delete someone else's review."""
    fake_film_repository.add(film)
    review = review_service.add_review(
        film_id=film.id,
        user_id=viewer_user.id,
        rating=7,
        review="Original review.",
    )

    with pytest.raises(UnauthorizedReviewDeleteError) as exc_info:
        review_service.delete_review(
            review_id=review.id,
            user_id=other_viewer_user.id,
        )

    assert exc_info.value.review_id == review.id
    assert exc_info.value.user_id == other_viewer_user.id


@pytest.mark.unit
def test_admin_can_delete_any_review(
    review_service: ReviewService,
    fake_film_repository: FakeFilmRepository,
    film: Film,
    viewer_user: User,
    admin_user: User,
) -> None:
    """Test administrator with is_admin=True can delete any review."""
    fake_film_repository.add(film)
    review = review_service.add_review(
        film_id=film.id,
        user_id=viewer_user.id,
        rating=5,
        review="Spam review.",
    )

    deleted = review_service.delete_review(
        review_id=review.id,
        user_id=admin_user.id,
        is_admin=True,
    )
    assert deleted is True
    assert len(review_service.list_reviews_for_film(film.id)) == 0


@pytest.mark.unit
def test_average_film_rating_updates_correctly_after_review_changes(
    review_service: ReviewService,
    fake_film_repository: FakeFilmRepository,
    film: Film,
    viewer_user: User,
    other_viewer_user: User,
    critic_user: User,
) -> None:
    """Test film total_reviews and average_rating update accurately upon create, update, and delete."""
    fake_film_repository.add(film)
    assert film.total_reviews == 0
    assert film.average_rating is None

    # Step 1: Add first review (rating 8) -> avg = 8.0
    r1 = review_service.add_review(film_id=film.id, user_id=viewer_user.id, rating=8, review="Good")
    assert film.total_reviews == 1
    assert film.average_rating == 8.0
    assert review_service.calculate_average_rating(film.id) == 8.0

    # Step 2: Add second review (rating 10) -> avg = (8 + 10) / 2 = 9.0
    r2 = review_service.add_review(film_id=film.id, user_id=other_viewer_user.id, rating=10, review="Great")
    assert film.total_reviews == 2
    assert film.average_rating == 9.0
    assert review_service.calculate_average_rating(film.id) == 9.0

    # Step 3: Add third review (rating 6) -> avg = (8 + 10 + 6) / 3 = 8.0
    r3 = review_service.add_review(film_id=film.id, user_id=critic_user.id, rating=6, review="Okay")
    assert film.total_reviews == 3
    assert film.average_rating == 8.0

    # Step 4: Author updates r3 from 6 to 9 -> avg = (8 + 10 + 9) / 3 = 9.0
    review_service.update_review(review_id=r3.id, user_id=critic_user.id, rating=9)
    assert film.total_reviews == 3
    assert film.average_rating == 9.0
    assert review_service.calculate_average_rating(film.id) == 9.0

    # Step 5: Author deletes r1 (8) -> remaining [10, 9] -> avg = 9.5
    review_service.delete_review(review_id=r1.id, user_id=viewer_user.id)
    assert film.total_reviews == 2
    assert film.average_rating == 9.5
    assert review_service.calculate_average_rating(film.id) == 9.5

    # Step 6: Delete remaining reviews -> resets to total_reviews=0 and average_rating=None
    review_service.delete_review(review_id=r2.id, user_id=other_viewer_user.id)
    review_service.delete_review(review_id=r3.id, user_id=critic_user.id)
    assert film.total_reviews == 0
    assert film.average_rating is None
    assert review_service.calculate_average_rating(film.id) is None
