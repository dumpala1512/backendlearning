from __future__ import annotations

import io
import json
import logging
import uuid
import pytest
from httpx import AsyncClient

from app.core.security import create_access_token
from app.logging.formatter import JSONFormatter
from app.middleware.request_id import get_current_request_id, request_id_ctx_var


@pytest.mark.asyncio
async def test_rule_1_route_duplicate_review_returns_409(auth_client: AsyncClient):
    """
    HTTP route test for Domain Rule 1:
    A user may submit only one review per film.
    Second attempt returns 409 Conflict with standard JSON error response format.
    """
    client = auth_client
    user_id = str(uuid.uuid4())

    # Create film
    film_res = await client.post(
        "/api/v1/films",
        json={
            "title": "Gladiator",
            "director": "Ridley Scott",
            "releaseYear": 2000,
            "genre": "Action",
            "description": "A former Roman General sets out to exact vengeance against the corrupt emperor.",
        },
    )
    assert film_res.status_code == 201
    film_id = film_res.json()["id"]

    # Submit first review
    rev_res = await client.post(
        f"/api/v1/films/{film_id}/reviews",
        json={
            "film_id": film_id,
            "rating": 10,
            "review": "What we do in life echoes in eternity! An absolute cinematic masterpiece.",
            "reviewer_display_name": "Maximus",
            "user_id": user_id,
        },
    )
    assert rev_res.status_code == 201

    # Attempt second review by same user for same film
    dup_res = await client.post(
        f"/api/v1/films/{film_id}/reviews",
        json={
            "film_id": film_id,
            "rating": 8,
            "review": "Trying to submit another review for Gladiator with the same user ID.",
            "reviewer_display_name": "Maximus Again",
            "user_id": user_id,
        },
    )
    assert dup_res.status_code == 409
    body = dup_res.json()
    assert body["type"] == "ReviewAlreadyExists"
    assert "already reviewed" in body["message"].lower()
    assert body["detail"]["film_id"] == film_id
    assert body["detail"]["user_id"] == user_id


@pytest.mark.asyncio
async def test_rule_2_route_permission_denied_on_update_returns_403(client: AsyncClient):
    """
    HTTP route test for Domain Rule 2:
    Only the original author may update review rating and review body.
    Other user update returns 403 Forbidden with standard JSON error format.
    Author update succeeds with 200 OK.
    """
    author_id = str(uuid.uuid4())
    other_user_id = str(uuid.uuid4())

    author_token = create_access_token({"sub": author_id, "username": "tyler", "role": "critic"})
    other_user_token = create_access_token({"sub": other_user_id, "username": "narrator", "role": "critic"})
    admin_token = create_access_token({"sub": str(uuid.uuid4()), "username": "admin_user", "role": "admin"})

    # Create film with admin token
    film_res = await client.post(
        "/api/v1/films",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "title": "Fight Club",
            "director": "David Fincher",
            "releaseYear": 1999,
            "genre": "Drama",
            "description": "An insomniac office worker and a devil-may-care soap maker form an underground fight club.",
        },
    )
    assert film_res.status_code == 201
    film_id = film_res.json()["id"]

    # Create review by author
    rev_res = await client.post(
        f"/api/v1/films/{film_id}/reviews",
        headers={"Authorization": f"Bearer {author_token}"},
        json={
            "film_id": film_id,
            "rating": 9,
            "review": "The first rule of Fight Club is you do not talk about Fight Club.",
            "reviewer_display_name": "Tyler",
            "user_id": author_id,
        },
    )
    assert rev_res.status_code == 201
    review_id = rev_res.json()["id"]

    # Attempt update by unauthorized user (via header or payload)
    unauth_res = await client.patch(
        f"/api/v1/reviews/{review_id}",
        headers={"Authorization": f"Bearer {other_user_token}", "X-User-Id": other_user_id},
        json={
            "rating": 1,
            "review": "Defaced by an unauthorized user who did not write this review originally.",
        },
    )
    assert unauth_res.status_code == 403
    body = unauth_res.json()
    assert body["type"] == "ReviewPermissionDenied"
    assert "author" in body["message"].lower()
    assert body["detail"]["review_id"] == review_id
    assert body["detail"]["user_id"] == other_user_id

    # Authorized update by original author succeeds
    auth_res = await client.patch(
        f"/api/v1/reviews/{review_id}",
        headers={"Authorization": f"Bearer {author_token}", "X-User-Id": author_id},
        json={
            "rating": 10,
            "review": "Updated review: timeless philosophical depth and brilliant editing throughout.",
        },
    )
    assert auth_res.status_code == 200
    assert auth_res.json()["rating"] == 10
    assert "timeless" in auth_res.json()["review"]


@pytest.mark.asyncio
async def test_rule_3_route_film_deletion_blocked_by_active_reviews_returns_409(auth_client: AsyncClient):
    client = auth_client
    """
    HTTP route test for Domain Rule 3:
    A film may not be soft deleted while it still has active reviews.
    DELETE returns 409 Conflict with standard JSON error format.
    After deleting review, soft delete succeeds.
    """
    film_res = await client.post(
        "/api/v1/films",
        json={
            "title": "The Prestige",
            "director": "Christopher Nolan",
            "releaseYear": 2006,
            "genre": "Drama",
            "description": "After a tragic accident, two stage magicians engage in a battle to create the ultimate illusion.",
        },
    )
    assert film_res.status_code == 201
    film_id = film_res.json()["id"]

    # Add active review
    rev_res = await client.post(
        f"/api/v1/films/{film_id}/reviews",
        json={
            "film_id": film_id,
            "rating": 10,
            "review": "Are you watching closely? Brilliant narrative structure with unbelievable misdirection.",
            "reviewer_display_name": "Borden",
        },
    )
    assert rev_res.status_code == 201
    review_id = rev_res.json()["id"]

    # Attempt to soft delete film -> blocked by active review
    del_film_blocked = await client.delete(f"/api/v1/films/{film_id}")
    assert del_film_blocked.status_code == 409
    body = del_film_blocked.json()
    assert body["type"] == "FilmHasActiveReviews"
    assert "active review" in body["message"].lower()
    assert body["detail"]["film_id"] == film_id
    assert body["detail"]["active_reviews_count"] == 1

    # Delete active review first
    del_rev = await client.delete(f"/api/v1/reviews/{review_id}")
    assert del_rev.status_code == 200

    # Now soft delete succeeds
    del_film_ok = await client.delete(f"/api/v1/films/{film_id}")
    assert del_film_ok.status_code == 200
    assert del_film_ok.json()["success"] is True


@pytest.mark.asyncio
async def test_request_id_middleware_headers(client: AsyncClient):
    """
    Verify RequestIDMiddleware:
    - Generates unique ID when none is provided
    - Retains provided X-Request-ID
    - Returns X-Request-ID in HTTP response headers
    """
    # Auto-generated ID
    res1 = await client.get("/health")
    assert res1.status_code == 200
    assert "x-request-id" in res1.headers
    assert "x-trace-id" not in res1.headers
    auto_id = res1.headers["x-request-id"]
    assert len(auto_id) > 10

    # Custom supplied ID
    custom_id = str(uuid.uuid4())
    res2 = await client.get("/health", headers={"X-Request-ID": custom_id})
    assert res2.status_code == 200
    assert res2.headers["x-request-id"] == custom_id
    assert "x-trace-id" not in res2.headers


def test_structured_json_logging_format():
    """
    Verify structured JSON logging:
    - Produces valid JSON
    - Includes timestamp (ISO-8601 UTC), level, logger, message
    - Includes request_id when context variable is set
    """
    formatter = JSONFormatter()
    logger = logging.getLogger("test_logger")
    log_output = io.StringIO()
    handler = logging.StreamHandler(log_output)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    test_request_id = "test-req-uuid-12345"
    token = request_id_ctx_var.set(test_request_id)
    try:
        logger.info("Test structured message", extra={"custom_key": "custom_val"})
    finally:
        request_id_ctx_var.reset(token)

    output = log_output.getvalue().strip()
    assert len(output) > 0

    log_entry = json.loads(output)
    assert log_entry["level"] == "INFO"
    assert log_entry["logger"] == "test_logger"
    assert log_entry["message"] == "Test structured message"
    assert log_entry["request_id"] == test_request_id
    assert log_entry["custom_key"] == "custom_val"
    assert "T" in log_entry["timestamp"]
    assert log_entry["timestamp"].endswith("Z")
