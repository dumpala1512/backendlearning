from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import uuid

from app.exceptions.film import FilmHasActiveReviewsError, FilmNotFoundError
from app.exceptions.review import (
    DuplicateReviewError,
    InvalidReviewRatingError,
    ReviewNotFoundError,
    UnauthorizedReviewDeleteError,
    UnauthorizedReviewUpdateError,
)
from app.models.film import Film
from app.models.review import Review


class FakeFilmRepository:
    """In-memory repository for Film entities."""

    def __init__(self, initial_films: list[Film] | None = None) -> None:
        self._films: dict[uuid.UUID, Film] = {}
        if initial_films:
            for film in initial_films:
                self.add(film)

    def add(self, film: Film) -> Film:
        film_id: uuid.UUID | None = getattr(film, "id", None)
        if film_id is None:
            film_id = uuid.uuid4()
            object.__setattr__(film, "id", film_id)
        self._films[film_id] = film
        return film

    def get_by_id(self, film_id: uuid.UUID) -> Film | None:
        return self._films.get(film_id)

    def list_all(self, active_only: bool = True) -> list[Film]:
        if active_only:
            return [f for f in self._films.values() if getattr(f, "is_active", True)]
        return list(self._films.values())

    def update(self, film_id: uuid.UUID, **kwargs: Any) -> Film | None:
        film = self._films.get(film_id)
        if film is None:
            return None
        for key, value in kwargs.items():
            if hasattr(film, key):
                setattr(film, key, value)
        return film

    def delete(self, film_id: uuid.UUID, hard_delete: bool = False) -> bool:
        if film_id not in self._films:
            return False
        if hard_delete:
            del self._films[film_id]
        else:
            self._films[film_id].is_active = False
        return True


class FakeReviewRepository:
    """In-memory repository for Review entities."""

    def __init__(self, initial_reviews: list[Review] | None = None) -> None:
        self._reviews: dict[uuid.UUID, Review] = {}
        if initial_reviews:
            for review in initial_reviews:
                self.add(review)

    def add(self, review: Review) -> Review:
        review_id: uuid.UUID | None = getattr(review, "id", None)
        if review_id is None:
            review_id = uuid.uuid4()
            object.__setattr__(review, "id", review_id)
        self._reviews[review_id] = review
        return review

    def get_by_id(self, review_id: uuid.UUID) -> Review | None:
        return self._reviews.get(review_id)

    def get_by_film_and_user(
        self, film_id: uuid.UUID, user_id: uuid.UUID
    ) -> Review | None:
        for r in self._reviews.values():
            if r.film_id == film_id and r.user_id == user_id:
                return r
        return None

    def list_by_film(self, film_id: uuid.UUID) -> list[Review]:
        return [r for r in self._reviews.values() if r.film_id == film_id]

    def list_all(self) -> list[Review]:
        return list(self._reviews.values())

    def update(self, review_id: uuid.UUID, **kwargs: Any) -> Review | None:
        review = self._reviews.get(review_id)
        if review is None:
            return None
        for key, value in kwargs.items():
            if hasattr(review, key):
                setattr(review, key, value)
        return review

    def delete(self, review_id: uuid.UUID) -> bool:
        if review_id not in self._reviews:
            return False
        del self._reviews[review_id]
        return True


class FakeRepository:
    """Unified fake repository containing both Film and Review stores."""

    def __init__(
        self,
        films: FakeFilmRepository | None = None,
        reviews: FakeReviewRepository | None = None,
    ) -> None:
        self.films = films or FakeFilmRepository()
        self.reviews = reviews or FakeReviewRepository()


class FilmService:
    """
    Synchronous domain service for Film business logic.
    Executes entirely in memory with no external I/O or async runtime.
    """

    def __init__(
        self,
        repository: FakeFilmRepository | None = None,
        review_repository: FakeReviewRepository | None = None,
    ) -> None:
        self.repository = repository or FakeFilmRepository()
        self.review_repository = review_repository or FakeReviewRepository()

    def create_film(
        self,
        title: str,
        director: str,
        release_year: int,
        genre: str,
        description: str = "",
    ) -> Film:
        title_clean = title.strip()
        if not title_clean:
            raise ValueError("Film title cannot be empty.")
        film = Film(
            id=uuid.uuid4(),
            title=title_clean,
            director=director.strip(),
            release_year=release_year,
            genre=genre.strip(),
            description=description.strip(),
            is_active=True,
            total_reviews=0,
            average_rating=None,
        )
        return self.repository.add(film)

    def get_film(self, film_id: uuid.UUID) -> Film:
        film = self.repository.get_by_id(film_id)
        if film is None or not getattr(film, "is_active", True):
            raise FilmNotFoundError(film_id=film_id)
        return film

    def list_films(
        self,
        genre: str | None = None,
        release_year: int | None = None,
        start_year: int | None = None,
        end_year: int | None = None,
        director: str | None = None,
        limit: int | None = None,
    ) -> list[Film]:
        results = self.repository.list_all(active_only=True)
        if genre is not None and genre.strip():
            genre_lower = genre.strip().lower()
            results = [f for f in results if f.genre.lower() == genre_lower]
        if release_year is not None:
            results = [f for f in results if f.release_year == release_year]
        if start_year is not None:
            results = [f for f in results if f.release_year >= start_year]
        if end_year is not None:
            results = [f for f in results if f.release_year <= end_year]
        if director is not None and director.strip():
            director_lower = director.strip().lower()
            results = [f for f in results if director_lower in f.director.lower()]
        if limit is not None:
            results = results[:limit]
        return results

    def update_film(self, film_id: uuid.UUID, **updates: Any) -> Film:
        film = self.get_film(film_id)
        updated = self.repository.update(film.id, **updates)
        if updated is None:
            raise FilmNotFoundError(film_id=film_id)
        return updated

    def delete_film(self, film_id: uuid.UUID) -> bool:
        film = self.get_film(film_id)
        active_reviews = self.review_repository.list_by_film(film.id)
        if active_reviews:
            raise FilmHasActiveReviewsError(
                film_id=film.id,
                active_reviews_count=len(active_reviews),
            )
        return self.repository.delete(film.id, hard_delete=False)

    def calculate_average_rating(self, film_id: uuid.UUID) -> float | None:
        _ = self.get_film(film_id)
        reviews = self.review_repository.list_by_film(film_id)
        if not reviews:
            return None
        return round(sum(r.rating for r in reviews) / len(reviews), 2)


class ReviewService:
    """
    Synchronous domain service for Review business logic.
    Enforces Domain Rule 1 (one review per user per film) and
    Domain Rule 2 (author-only updates and deletions).
    Executes entirely in memory with no external I/O or async runtime.
    """

    def __init__(
        self,
        repository: FakeReviewRepository | None = None,
        film_repository: FakeFilmRepository | None = None,
    ) -> None:
        self.repository = repository or FakeReviewRepository()
        self.film_repository = film_repository or FakeFilmRepository()

    def _update_film_metrics(self, film_id: uuid.UUID) -> None:
        film = self.film_repository.get_by_id(film_id)
        if film is not None:
            film_reviews = self.repository.list_by_film(film_id)
            film.total_reviews = len(film_reviews)
            if film_reviews:
                film.average_rating = round(
                    sum(r.rating for r in film_reviews) / len(film_reviews), 2
                )
            else:
                film.average_rating = None

    def add_review(
        self,
        film_id: uuid.UUID,
        user_id: uuid.UUID,
        rating: int,
        review: str,
        reviewer_display_name: str = "Anonymous Critic",
    ) -> Review:
        # Check film exists and is active
        film = self.film_repository.get_by_id(film_id)
        if film is None or not getattr(film, "is_active", True):
            raise FilmNotFoundError(film_id=film_id)

        # Validate rating range (1-10)
        if rating < 1 or rating > 10:
            raise InvalidReviewRatingError(rating=rating, min_rating=1, max_rating=10)

        # Enforce Rule 1: One review per user per film
        existing = self.repository.get_by_film_and_user(film_id, user_id)
        if existing is not None:
            raise DuplicateReviewError(
                film_id=film_id,
                user_id=user_id,
                review_id=existing.id,
            )

        new_review = Review(
            id=uuid.uuid4(),
            film_id=film_id,
            user_id=user_id,
            rating=rating,
            review=review.strip(),
            reviewer_display_name=reviewer_display_name.strip(),
            created_at=datetime.now(timezone.utc),
        )
        self.repository.add(new_review)
        self._update_film_metrics(film_id)
        return new_review

    def get_review(self, review_id: uuid.UUID) -> Review:
        review = self.repository.get_by_id(review_id)
        if review is None:
            raise ReviewNotFoundError(review_id=review_id)
        return review

    def list_reviews_for_film(
        self,
        film_id: uuid.UUID,
        min_rating: int | None = None,
        max_rating: int | None = None,
    ) -> list[Review]:
        film = self.film_repository.get_by_id(film_id)
        if film is None or not getattr(film, "is_active", True):
            raise FilmNotFoundError(film_id=film_id)

        reviews = self.repository.list_by_film(film_id)
        if min_rating is not None:
            reviews = [r for r in reviews if r.rating >= min_rating]
        if max_rating is not None:
            reviews = [r for r in reviews if r.rating <= max_rating]
        return reviews

    def update_review(
        self,
        review_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
        rating: int | None = None,
        review: str | None = None,
        is_admin: bool = False,
    ) -> Review:
        existing = self.get_review(review_id)

        # Enforce Rule 2: Only original author or admin can edit
        if not is_admin and existing.user_id is not None:
            if user_id is None or existing.user_id != user_id:
                raise UnauthorizedReviewUpdateError(
                    review_id=review_id,
                    user_id=user_id,
                )

        updates: dict[str, Any] = {}
        if rating is not None:
            if rating < 1 or rating > 10:
                raise InvalidReviewRatingError(rating=rating, min_rating=1, max_rating=10)
            updates["rating"] = rating
        if review is not None:
            updates["review"] = review.strip()

        updated = self.repository.update(review_id, **updates)
        if updated is None:
            raise ReviewNotFoundError(review_id=review_id)

        self._update_film_metrics(updated.film_id)
        return updated

    def delete_review(
        self,
        review_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
        is_admin: bool = False,
    ) -> bool:
        existing = self.get_review(review_id)

        # Enforce Rule 2: Only original author or admin can delete
        if not is_admin and existing.user_id is not None:
            if user_id is None or existing.user_id != user_id:
                raise UnauthorizedReviewDeleteError(
                    review_id=review_id,
                    user_id=user_id,
                )

        film_id = existing.film_id
        deleted = self.repository.delete(review_id)
        if not deleted:
            raise ReviewNotFoundError(review_id=review_id)

        self._update_film_metrics(film_id)
        return True

    def calculate_average_rating(self, film_id: uuid.UUID) -> float | None:
        film = self.film_repository.get_by_id(film_id)
        if film is None or not getattr(film, "is_active", True):
            raise FilmNotFoundError(film_id=film_id)

        reviews = self.repository.list_by_film(film_id)
        if not reviews:
            return None
        return round(sum(r.rating for r in reviews) / len(reviews), 2)
