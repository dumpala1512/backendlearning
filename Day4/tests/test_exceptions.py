from __future__ import annotations

import json
import uuid
import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from app.exceptions import (
    AuthenticationError,
    DomainError,
    DuplicateEntityError,
    EntityNotFoundError,
    FilmAlreadyExistsError,
    FilmHasActiveReviewsError,
    FilmNotFoundError,
    InvalidCredentialsError,
    InvalidReviewRatingError,
    PermissionDeniedError,
    ReviewAlreadyExistsError,
    ReviewNotFoundError,
    ReviewPermissionDeniedError,
    UserAlreadyExistsError,
    UserNotFoundError,
    ValidationError,
    create_error_response,
    register_exception_handlers,
)


def test_base_domain_exceptions_status_codes_and_messages():
    # DomainError default
    base_err = DomainError()
    assert base_err.status_code == status.HTTP_400_BAD_REQUEST
    assert base_err.message == "A domain business logic error occurred."
    assert base_err.error_type == "Domain"
    assert str(base_err) == base_err.message
    assert base_err.to_dict()["status_code"] == 400

    # Custom message & status code override
    custom_err = DomainError(message="Custom fault", status_code=status.HTTP_418_IM_A_TEAPOT)
    assert custom_err.status_code == 418
    assert custom_err.message == "Custom fault"

    # EntityNotFoundError
    not_found = EntityNotFoundError()
    assert not_found.status_code == status.HTTP_404_NOT_FOUND
    assert not_found.error_type == "EntityNotFound"
    assert "not found" in not_found.message.lower()

    # DuplicateEntityError
    dup_err = DuplicateEntityError()
    assert dup_err.status_code == status.HTTP_409_CONFLICT
    assert dup_err.error_type == "DuplicateEntity"

    # PermissionDeniedError
    perm_err = PermissionDeniedError()
    assert perm_err.status_code == status.HTTP_403_FORBIDDEN
    assert perm_err.error_type == "PermissionDenied"

    # ValidationError
    val_err = ValidationError()
    assert val_err.status_code == status.HTTP_400_BAD_REQUEST
    assert val_err.error_type == "Validation"

    # AuthenticationError
    auth_err = AuthenticationError()
    assert auth_err.status_code == status.HTTP_401_UNAUTHORIZED
    assert auth_err.error_type == "Authentication"


def test_film_exceptions():
    test_id = uuid.uuid4()

    # FilmNotFoundError
    fnf = FilmNotFoundError(film_id=test_id)
    assert fnf.status_code == status.HTTP_404_NOT_FOUND
    assert fnf.film_id == test_id
    assert fnf.detail["film_id"] == str(test_id)
    assert f"Film with id {test_id} not found." in fnf.message
    assert fnf.error_type == "FilmNotFound"

    # FilmHasActiveReviewsError
    fhar = FilmHasActiveReviewsError(film_id=test_id, active_reviews_count=3)
    assert fhar.status_code == status.HTTP_409_CONFLICT
    assert fhar.film_id == test_id
    assert fhar.active_reviews_count == 3
    assert fhar.detail["film_id"] == str(test_id)
    assert fhar.detail["active_reviews_count"] == 3
    assert "3 active reviews" in fhar.message
    assert fhar.error_type == "FilmHasActiveReviews"

    # FilmAlreadyExistsError
    fae = FilmAlreadyExistsError(title="Inception", release_year=2010)
    assert fae.status_code == status.HTTP_409_CONFLICT
    assert fae.title == "Inception"
    assert fae.release_year == 2010
    assert fae.detail["title"] == "Inception"
    assert fae.detail["release_year"] == 2010
    assert "Inception" in fae.message
    assert fae.error_type == "FilmAlreadyExists"


def test_review_exceptions():
    rev_id = uuid.uuid4()
    film_id = uuid.uuid4()
    user_id = uuid.uuid4()

    # ReviewNotFoundError
    rnf = ReviewNotFoundError(review_id=rev_id)
    assert rnf.status_code == status.HTTP_404_NOT_FOUND
    assert rnf.review_id == rev_id
    assert rnf.detail["review_id"] == str(rev_id)
    assert f"Review with id {rev_id} not found." in rnf.message
    assert rnf.error_type == "ReviewNotFound"

    # ReviewAlreadyExistsError
    rae = ReviewAlreadyExistsError(film_id=film_id, user_id=user_id, review_id=rev_id)
    assert rae.status_code == status.HTTP_409_CONFLICT
    assert rae.film_id == film_id
    assert rae.user_id == user_id
    assert rae.review_id == rev_id
    assert rae.detail["film_id"] == str(film_id)
    assert rae.detail["user_id"] == str(user_id)
    assert rae.detail["review_id"] == str(rev_id)
    assert "already reviewed" in rae.message.lower()
    assert rae.error_type == "ReviewAlreadyExists"

    # ReviewPermissionDeniedError
    rpd = ReviewPermissionDeniedError(review_id=rev_id, user_id=user_id)
    assert rpd.status_code == status.HTTP_403_FORBIDDEN
    assert rpd.review_id == rev_id
    assert rpd.user_id == user_id
    assert rpd.detail["review_id"] == str(rev_id)
    assert rpd.detail["user_id"] == str(user_id)
    assert "author" in rpd.message.lower()
    assert rpd.error_type == "ReviewPermissionDenied"

    # InvalidReviewRatingError
    irr = InvalidReviewRatingError(rating=15, min_rating=1, max_rating=10)
    assert irr.status_code == status.HTTP_400_BAD_REQUEST
    assert irr.rating == 15
    assert irr.detail["rating"] == 15
    assert "between 1 and 10" in irr.message
    assert irr.error_type == "InvalidReviewRating"


def test_user_exceptions():
    uid = uuid.uuid4()

    # UserNotFoundError with UUID
    unf_id = UserNotFoundError(user_id=uid)
    assert unf_id.status_code == status.HTTP_404_NOT_FOUND
    assert unf_id.user_id == uid
    assert unf_id.detail["user_id"] == str(uid)
    assert f"User with id {uid} not found." in unf_id.message
    assert unf_id.error_type == "UserNotFound"

    # UserNotFoundError with username
    unf_user = UserNotFoundError(username="cinephile")
    assert unf_user.username == "cinephile"
    assert unf_user.detail["username"] == "cinephile"
    assert "User with username 'cinephile' not found." in unf_user.message

    # UserNotFoundError with positional message string
    unf_msg = UserNotFoundError("No user profile found. Please register or seed a user first.")
    assert unf_msg.status_code == status.HTTP_404_NOT_FOUND
    assert unf_msg.message == "No user profile found. Please register or seed a user first."

    # UserAlreadyExistsError
    uae = UserAlreadyExistsError(field="email", value="test@example.com")
    assert uae.status_code == status.HTTP_409_CONFLICT
    assert uae.field == "email"
    assert uae.value == "test@example.com"
    assert uae.detail["email"] == "test@example.com"
    assert "User with email 'test@example.com' already exists." in uae.message
    assert uae.error_type == "UserAlreadyExists"

    # InvalidCredentialsError
    ic = InvalidCredentialsError()
    assert ic.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Invalid username or password" in ic.message
    assert ic.error_type == "InvalidCredentials"


def test_exception_handlers_in_fastapi():
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/trigger/not-found")
    def trigger_not_found():
        raise FilmNotFoundError(film_id=uuid.UUID("11111111-1111-1111-1111-111111111111"))

    @app.get("/trigger/conflict")
    def trigger_conflict():
        raise FilmHasActiveReviewsError(
            film_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
            active_reviews_count=2,
        )

    @app.get("/trigger/forbidden")
    def trigger_forbidden():
        raise ReviewPermissionDeniedError(
            review_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
            user_id=uuid.UUID("33333333-3333-3333-3333-333333333333"),
        )

    @app.get("/trigger/unauthorized")
    def trigger_unauthorized():
        raise InvalidCredentialsError()

    @app.get("/trigger/validation")
    def trigger_validation():
        raise InvalidReviewRatingError(rating=0)

    client = TestClient(app)

    # 404 Not Found
    res_404 = client.get("/trigger/not-found")
    assert res_404.status_code == 404
    data_404 = res_404.json()
    assert data_404["status_code"] == 404
    assert data_404["type"] == "FilmNotFound"
    assert "not found" in data_404["message"].lower()
    assert data_404["detail"]["film_id"] == "11111111-1111-1111-1111-111111111111"

    # 409 Conflict
    res_409 = client.get("/trigger/conflict")
    assert res_409.status_code == 409
    data_409 = res_409.json()
    assert data_409["status_code"] == 409
    assert data_409["type"] == "FilmHasActiveReviews"
    assert "active reviews" in data_409["message"].lower()

    # 403 Forbidden
    res_403 = client.get("/trigger/forbidden")
    assert res_403.status_code == 403
    data_403 = res_403.json()
    assert data_403["status_code"] == 403
    assert data_403["type"] == "ReviewPermissionDenied"
    assert "author" in data_403["message"].lower()

    # 401 Unauthorized
    res_401 = client.get("/trigger/unauthorized")
    assert res_401.status_code == 401
    data_401 = res_401.json()
    assert data_401["status_code"] == 401
    assert data_401["type"] == "InvalidCredentials"

    # 400 Bad Request
    res_400 = client.get("/trigger/validation")
    assert res_400.status_code == 400
    data_400 = res_400.json()
    assert data_400["status_code"] == 400
    assert data_400["type"] == "InvalidReviewRating"
