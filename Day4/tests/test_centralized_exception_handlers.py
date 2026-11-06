from __future__ import annotations

import uuid
from httpx import AsyncClient
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers import get_user_headers, register_user


# ===========================================================================
# Requirement 3: Centralized Exception Handler Tests via Actual API Routes
# ===========================================================================


@pytest.mark.integration
async def test_not_found_exception_via_api_route(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """
    Requirement 3: Intentionally trigger a NotFoundException (FilmNotFoundError)
    through a real API route (GET /films/{id}).

    Verifies:
    - HTTP status code is 404 Not Found
    - Response JSON contains standardized format:
      {
          "status_code": 404,
          "type": "FilmNotFound",
          "message": "...",
          "detail": ...
      }
    - "type" matches expected error type
    - "message" is non-empty
    - Exception propagates through middleware into centralized exception handler
    """
    # Arrange: Valid auth headers and non-existent random UUID
    headers = await get_user_headers(client, db_session, role="viewer", username="viewer_not_found_test")
    missing_film_id = uuid.uuid4()

    # Act: Request non-existent film through actual API route
    response = await client.get(f"/films/{missing_film_id}", headers=headers)

    # Assert: Status code
    assert response.status_code == 404

    # Assert: Response JSON format
    data = response.json()
    assert "type" in data
    assert "message" in data
    assert data["type"] == "FilmNotFound"
    assert len(data["message"]) > 0
    assert str(missing_film_id) in data["message"] or "not found" in data["message"].lower()

    # Detail contains relevant structured context
    assert "detail" in data
    assert str(missing_film_id) in str(data["detail"])


@pytest.mark.integration
async def test_conflict_exception_duplicate_review_via_api_route(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """
    Requirement 3: Intentionally trigger a ConflictException (ReviewAlreadyExistsError)
    through a real API route (POST /films/{id}/reviews).

    Domain Rule 1: A user may submit only one review per film.
    A second review attempt by the same user triggers ReviewAlreadyExistsError (409 Conflict).

    Verifies:
    - HTTP status code is 409 Conflict
    - Response JSON format contains "type" and non-empty "message"
    - "type" == "ReviewAlreadyExists"
    """
    # Arrange: Admin to create a film, and Critic to post reviews
    admin_headers = await get_user_headers(client, db_session, role="admin", username="admin_conflict_tester")
    critic_headers = await get_user_headers(client, db_session, role="critic", username="critic_conflict_tester")

    # Create film
    film_payload = {
        "title": "Memento",
        "director": "Christopher Nolan",
        "release_year": 2000,
        "genre": "Mystery",
        "description": "A man with short-term memory loss attempts to track down his wife's murderer.",
    }
    film_res = await client.post("/films", json=film_payload, headers=admin_headers)
    assert film_res.status_code == 201
    film_id = film_res.json()["id"]

    review_payload = {
        "film_id": film_id,
        "rating": 9,
        "review": "A brilliant exploration of perception, memory, and non-linear narrative structure.",
        "reviewer_display_name": "Leonard Shelby",
    }

    # First review submission -> 201 Created
    first_res = await client.post(f"/films/{film_id}/reviews", json=review_payload, headers=critic_headers)
    assert first_res.status_code == 201

    # Second review submission by same critic for same film -> 409 Conflict
    dup_res = await client.post(f"/films/{film_id}/reviews", json=review_payload, headers=critic_headers)

    # Assert
    assert dup_res.status_code == 409
    data = dup_res.json()
    assert "type" in data
    assert "message" in data
    assert data["type"] == "ReviewAlreadyExists"
    assert len(data["message"]) > 0
    assert "already reviewed" in data["message"].lower()


@pytest.mark.integration
async def test_conflict_exception_film_with_active_reviews_via_api_route(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """
    Requirement 3: Intentionally trigger FilmHasActiveReviewsError (409 Conflict)
    via DELETE /films/{film_id} when film still has active reviews.
    """
    admin_headers = await get_user_headers(client, db_session, role="admin", username="admin_active_rev_test")
    critic_headers = await get_user_headers(client, db_session, role="critic", username="critic_active_rev_test")

    # Create film
    film_res = await client.post(
        "/films",
        headers=admin_headers,
        json={
            "title": "Dunkirk",
            "director": "Christopher Nolan",
            "release_year": 2017,
            "genre": "War",
            "description": "Allied soldiers from Belgium, the British Empire, and France are surrounded by the German Army.",
        },
    )
    assert film_res.status_code == 201
    film_id = film_res.json()["id"]

    # Add active review
    rev_res = await client.post(
        f"/films/{film_id}/reviews",
        headers=critic_headers,
        json={
            "film_id": film_id,
            "rating": 8,
            "review": "Miraculous evacuation told through land, sea, and air perspectives with ticking suspense.",
            "reviewer_display_name": "Tommy",
        },
    )
    assert rev_res.status_code == 201

    # Act: Attempt to delete film while review is active
    delete_res = await client.delete(f"/films/{film_id}", headers=admin_headers)

    # Assert: 409 Conflict handled centrally
    assert delete_res.status_code == 409
    data = delete_res.json()
    assert data["type"] == "FilmHasActiveReviews"
    assert "active review" in data["message"].lower()
    assert data["detail"]["film_id"] == film_id
    assert data["detail"]["active_reviews_count"] == 1


@pytest.mark.integration
async def test_validation_exception_mismatched_id_via_api_route(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """
    Requirement 3: Intentionally trigger a ValidationException (ValidationError)
    through a real API route (POST /films/{id}/reviews with mismatched path & body IDs).

    Verifies:
    - HTTP status code is 400 Bad Request
    - Response JSON contains "type" and "message"
    - "type" matches expected error type
    - "message" is non-empty
    """
    critic_headers = await get_user_headers(client, db_session, role="critic", username="critic_val_test")
    path_film_id = uuid.uuid4()
    body_film_id = uuid.uuid4()

    payload = {
        "film_id": str(body_film_id),
        "rating": 8,
        "review": "Valid length review text that exceeds fifty characters easily for this test scenario.",
        "reviewer_display_name": "Test Critic",
    }

    response = await client.post(f"/films/{path_film_id}/reviews", json=payload, headers=critic_headers)

    assert response.status_code == 400
    data = response.json()
    assert data["type"] == "Validation"
    assert len(data["message"]) > 0
    assert "does not match" in data["message"].lower()
    assert data["detail"]["film_id"] == str(path_film_id)
    assert data["detail"]["payload_film_id"] == str(body_film_id)


@pytest.mark.integration
async def test_permission_denied_exception_via_api_route(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """
    Requirement 3: Intentionally trigger PermissionDeniedError (403 Forbidden)
    via attempting to submit a review claiming another user's identity.
    """
    critic_headers = await get_user_headers(client, db_session, role="critic", username="critic_perm_tester")
    admin_headers = await get_user_headers(client, db_session, role="admin", username="admin_perm_tester")

    # Create film
    film_res = await client.post(
        "/films",
        headers=admin_headers,
        json={
            "title": "Tenet",
            "director": "Christopher Nolan",
            "release_year": 2020,
            "genre": "Action",
            "description": "Armed with only one word, Tenet, and fighting for the survival of the world.",
        },
    )
    film_id = film_res.json()["id"]

    # Spoofed user ID
    spoofed_user_id = str(uuid.uuid4())
    payload = {
        "film_id": film_id,
        "rating": 7,
        "review": "A complex temporal inversion puzzle that rewards repeat viewings thoroughly.",
        "reviewer_display_name": "Spoofed Reviewer",
        "user_id": spoofed_user_id,
    }

    response = await client.post(f"/films/{film_id}/reviews", json=payload, headers=critic_headers)

    assert response.status_code == 403
    data = response.json()
    assert data["type"] == "PermissionDenied"
    assert "identity" in data["message"].lower() or "permission" in data["message"].lower()
