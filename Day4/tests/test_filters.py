from __future__ import annotations

import uuid
import pytest

from app.exceptions.review import InvalidReviewRatingError
from app.models.film import Film
from app.models.user import User
from tests.fakes import FilmService, ReviewService


@pytest.mark.unit
@pytest.mark.parametrize(
    "genre, expected_count, expected_titles",
    [
        ("Sci-Fi", 2, ["Inception", "Interstellar"]),
        ("Action", 1, ["The Dark Knight"]),
        ("Crime", 2, ["Pulp Fiction", "The Godfather"]),
        ("Animation", 1, ["Spirited Away"]),
        ("Drama", 1, ["Parasite"]),
        ("Western", 0, []),
        ("sci-fi", 2, ["Inception", "Interstellar"]),  # Case-insensitivity check
        ("CRIME", 2, ["Pulp Fiction", "The Godfather"]),  # Uppercase check
    ],
)
def test_filtering_films_by_genre(
    film_service: FilmService,
    multiple_films: list[Film],
    genre: str,
    expected_count: int,
    expected_titles: list[str],
) -> None:
    """Parametrized test for multi-genre filtering including case insensitivity."""
    for film in multiple_films:
        film_service.repository.add(film)

    matched = film_service.list_films(genre=genre)

    assert len(matched) == expected_count
    matched_titles = [f.title for f in matched]
    for expected_title in expected_titles:
        assert expected_title in matched_titles


@pytest.mark.unit
def test_films_conform_to_immutable_genres(
    multiple_films: list[Film],
    immutable_genres: tuple[str, ...],
) -> None:
    """Verify all sample test films belong to the module-scoped genre specification."""
    for film in multiple_films:
        assert film.genre in immutable_genres



@pytest.mark.unit
@pytest.mark.parametrize(
    "start_year, end_year, expected_count, expected_titles",
    [
        (2000, 2015, 4, ["The Dark Knight", "Spirited Away", "Inception", "Interstellar"]),
        (1970, 1999, 2, ["The Godfather", "Pulp Fiction"]),
        (2019, 2025, 1, ["Parasite"]),
        (1950, 1969, 0, []),
        (2010, 2010, 1, ["Inception"]),  # Single exact year boundary
    ],
)
def test_filtering_films_by_release_year(
    film_service: FilmService,
    multiple_films: list[Film],
    start_year: int,
    end_year: int,
    expected_count: int,
    expected_titles: list[str],
) -> None:
    """Parametrized test for release year range boundaries."""
    for film in multiple_films:
        film_service.repository.add(film)

    matched = film_service.list_films(start_year=start_year, end_year=end_year)

    assert len(matched) == expected_count
    matched_titles = [f.title for f in matched]
    for expected_title in expected_titles:
        assert expected_title in matched_titles


@pytest.mark.unit
@pytest.mark.parametrize(
    "genre, start_year, end_year, expected_count, expected_titles",
    [
        ("Sci-Fi", 2010, 2012, 1, ["Inception"]),
        ("Sci-Fi", 2013, 2020, 1, ["Interstellar"]),
        ("Crime", 1990, 2000, 1, ["Pulp Fiction"]),
        ("Crime", 1970, 1980, 1, ["The Godfather"]),
        ("Action", 2015, 2025, 0, []),
    ],
)
def test_filtering_films_by_both_genre_and_year(
    film_service: FilmService,
    multiple_films: list[Film],
    genre: str,
    start_year: int,
    end_year: int,
    expected_count: int,
    expected_titles: list[str],
) -> None:
    """Parametrized test for compound multi-attribute filtering (genre and release year)."""
    for film in multiple_films:
        film_service.repository.add(film)

    matched = film_service.list_films(
        genre=genre,
        start_year=start_year,
        end_year=end_year,
    )

    assert len(matched) == expected_count
    matched_titles = [f.title for f in matched]
    for expected_title in expected_titles:
        assert expected_title in matched_titles


@pytest.mark.unit
@pytest.mark.parametrize(
    "ratings, expected_average",
    [
        ([10, 8], 9.0),
        ([7, 8, 9], 8.0),
        ([5], 5.0),
        ([9, 9, 10], 9.33),
        ([1, 2, 3, 4, 5], 3.0),
        ([10, 10, 10, 10], 10.0),
        ([], None),
    ],
)
def test_average_rating_calculations(
    review_service: ReviewService,
    film_service: FilmService,
    film: Film,
    ratings: list[int],
    expected_average: float | None,
) -> None:
    """Parametrized test for mathematical correctness of film rating averages."""
    film_service.repository.add(film)

    for i, rating in enumerate(ratings):
        user_id = uuid.uuid4()
        review_service.add_review(
            film_id=film.id,
            user_id=user_id,
            rating=rating,
            review=f"Review score {rating}",
            reviewer_display_name=f"Critic {i}",
        )

    computed = review_service.calculate_average_rating(film.id)
    assert computed == expected_average
    assert film.average_rating == expected_average


@pytest.mark.unit
@pytest.mark.parametrize(
    "rating, is_valid",
    [
        (1, True),
        (5, True),
        (10, True),
        (0, False),
        (-1, False),
        (-10, False),
        (11, False),
        (15, False),
        (100, False),
    ],
)
def test_rating_boundary_validation(
    review_service: ReviewService,
    film_service: FilmService,
    film: Film,
    viewer_user: User,
    valid_rating_range: tuple[int, int],
    rating: int,
    is_valid: bool,
) -> None:
    """Parametrized boundary value test for review rating limits [1, 10]."""
    min_rating, max_rating = valid_rating_range
    film_service.repository.add(film)

    if is_valid:
        review = review_service.add_review(
            film_id=film.id,
            user_id=viewer_user.id,
            rating=rating,
            review="Valid review body text.",
        )
        assert review.rating == rating
    else:
        with pytest.raises(InvalidReviewRatingError) as exc_info:
            review_service.add_review(
                film_id=film.id,
                user_id=viewer_user.id,
                rating=rating,
                review="Invalid review rating test.",
            )
        assert exc_info.value.rating == rating
        assert exc_info.value.min_rating == min_rating
        assert exc_info.value.max_rating == max_rating
