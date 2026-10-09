from __future__ import annotations

import uuid
import pytest
from httpx import AsyncClient

from app.core.security import create_access_token


@pytest.mark.asyncio
async def test_me_endpoint_accessible_to_all_authenticated_roles(
    admin_client: AsyncClient,
    critic_client: AsyncClient,
    viewer_client: AsyncClient,
    client: AsyncClient,
):
    """
    GET /api/v1/me and GET /me:
    Accessible to any authenticated user regardless of role (Admin, Critic, Viewer).
    Rejects unauthenticated requests with 401 Unauthorized.
    """
    # 1. Admin accesses /me
    res_admin = await admin_client.get("/api/v1/me")
    assert res_admin.status_code == 200
    assert res_admin.json()["role"] == "admin"
    assert res_admin.json()["username"] == "sarah_admin"

    # 2. Critic accesses /me
    res_critic = await critic_client.get("/api/v1/me")
    assert res_critic.status_code == 200
    assert res_critic.json()["role"] == "critic"
    assert res_critic.json()["username"] == "marcus_critic"

    # 3. Viewer accesses /me
    res_viewer = await viewer_client.get("/api/v1/me")
    assert res_viewer.status_code == 200
    assert res_viewer.json()["role"] == "viewer"
    assert res_viewer.json()["username"] == "alex_viewer"

    # 4. Root alias /me also works
    res_root_me = await viewer_client.get("/me")
    assert res_root_me.status_code == 200
    assert res_root_me.json()["role"] == "viewer"

    # 5. Unauthenticated request to /me returns 401
    res_unauth = await client.get("/api/v1/me")
    assert res_unauth.status_code == 401


@pytest.mark.asyncio
async def test_admin_permissions_on_films_and_reviews(
    admin_client: AsyncClient,
    db_session,
):
    """
    Admins can:
    - Create any film (201)
    - Update any film (200)
    - Soft-delete any film (200)
    - Create reviews (201)
    - Update any review (200)
    - Delete any review (200)
    - Access Admin stats (200)
    """
    # 1. Admin creates film
    film_payload = {
        "title": "Interstellar",
        "director": "Christopher Nolan",
        "releaseYear": 2014,
        "genre": "Sci-Fi",
        "description": "A team of explorers travel through a wormhole in space in an attempt to ensure humanity's survival.",
    }
    film_res = await admin_client.post("/api/v1/films", json=film_payload)
    assert film_res.status_code == 201
    film_id = film_res.json()["id"]

    # 2. Admin updates film
    patch_res = await admin_client.patch(
        f"/api/v1/films/{film_id}",
        json={"description": "Updated epic sci-fi description."},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["description"] == "Updated epic sci-fi description."

    # 3. Admin creates review
    rev_payload = {
        "film_id": film_id,
        "rating": 10,
        "review": "A transcendent masterpiece blending theoretical physics with profound emotional depth.",
        "reviewer_display_name": "Sarah Connor",
    }
    rev_res = await admin_client.post(f"/api/v1/films/{film_id}/reviews", json=rev_payload)
    assert rev_res.status_code == 201
    review_id = rev_res.json()["id"]

    # 4. Admin updates review
    rev_patch_res = await admin_client.patch(
        f"/api/v1/reviews/{review_id}",
        json={"rating": 9, "review": "Updated review text: Absolutely breathtaking soundtrack and visuals."},
    )
    assert rev_patch_res.status_code == 200
    assert rev_patch_res.json()["rating"] == 9

    # 5. Admin accesses stats
    stats_res = await admin_client.get("/api/v1/admin/stats")
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert "total_films" in stats
    assert "total_reviews" in stats
    assert "overall_average_rating" in stats
    assert "top_reviewer_username" in stats

    # 6. Admin deletes review
    del_rev_res = await admin_client.delete(f"/api/v1/reviews/{review_id}")
    assert del_rev_res.status_code == 200
    assert del_rev_res.json()["success"] is True

    # 7. Admin soft-deletes film
    del_film_res = await admin_client.delete(f"/api/v1/films/{film_id}")
    assert del_film_res.status_code == 200
    assert del_film_res.json()["success"] is True


@pytest.mark.asyncio
async def test_critic_permissions_and_restrictions(
    admin_client: AsyncClient,
    critic_client: AsyncClient,
    client: AsyncClient,
):
    """
    Critics:
    - CANNOT create film (403 Forbidden)
    - CANNOT update film (403 Forbidden)
    - CANNOT delete film (403 Forbidden)
    - CAN create reviews (201 Created)
    - CAN update their own reviews (200 OK)
    - CANNOT update other critics' reviews (403 Forbidden)
    - CAN delete their own reviews (200 OK)
    - CANNOT delete other critics' reviews (403 Forbidden)
    - CANNOT access Admin stats (403 Forbidden)
    """
    # 1. Admin sets up a film for testing
    film_res = await admin_client.post(
        "/api/v1/films",
        json={
            "title": "Memento",
            "director": "Christopher Nolan",
            "releaseYear": 2000,
            "genre": "Mystery",
            "description": "A man with short-term memory loss attempts to track down his wife's murderer.",
        },
    )
    assert film_res.status_code == 201
    film_id = film_res.json()["id"]

    # 2. Critic attempts to create film -> 403 Forbidden
    critic_film_create = await critic_client.post(
        "/api/v1/films",
        json={
            "title": "Unauthorized Film",
            "director": "Nobody",
            "releaseYear": 2024,
            "genre": "Drama",
            "description": "Should fail with 403 forbidden.",
        },
    )
    assert critic_film_create.status_code == 403
    assert critic_film_create.json()["type"] == "PermissionDenied"

    # 3. Critic attempts to update film -> 403 Forbidden
    critic_film_update = await critic_client.patch(
        f"/api/v1/films/{film_id}",
        json={"title": "Hacked Title"},
    )
    assert critic_film_update.status_code == 403

    # 4. Critic attempts to delete film -> 403 Forbidden
    critic_film_delete = await critic_client.delete(f"/api/v1/films/{film_id}")
    assert critic_film_delete.status_code == 403

    # 5. Critic attempts to access admin stats -> 403 Forbidden
    critic_stats = await critic_client.get("/api/v1/admin/stats")
    assert critic_stats.status_code == 403

    # 6. Critic 1 creates review under their own identity
    c1_id = str(uuid.uuid4())
    c1_token = create_access_token({"sub": c1_id, "username": "critic_one", "role": "critic"})
    c1_client = client
    c1_client.headers.update({"Authorization": f"Bearer {c1_token}"})

    c1_rev_res = await c1_client.post(
        f"/api/v1/films/{film_id}/reviews",
        json={
            "film_id": film_id,
            "rating": 9,
            "review": "A brilliant non-linear puzzle that redefines psychological thriller storytelling.",
            "reviewer_display_name": "Critic One",
            "user_id": c1_id,
        },
    )
    assert c1_rev_res.status_code == 201
    review_id = c1_rev_res.json()["id"]

    # 7. Critic 2 attempts to update Critic 1's review -> 403 Forbidden
    c2_id = str(uuid.uuid4())
    c2_token = create_access_token({"sub": c2_id, "username": "critic_two", "role": "critic"})
    c2_client = client
    c2_client.headers.update({"Authorization": f"Bearer {c2_token}"})

    c2_update_res = await c2_client.patch(
        f"/api/v1/reviews/{review_id}",
        json={"rating": 1, "review": "Vandalized review attempt by another critic who did not write this."},
    )
    assert c2_update_res.status_code == 403

    # 8. Critic 2 attempts to delete Critic 1's review -> 403 Forbidden
    c2_del_res = await c2_client.delete(f"/api/v1/reviews/{review_id}")
    assert c2_del_res.status_code == 403

    # 9. Critic 1 updates their OWN review -> 200 OK
    c1_client.headers.update({"Authorization": f"Bearer {c1_token}"})
    c1_update_res = await c1_client.patch(
        f"/api/v1/reviews/{review_id}",
        json={"rating": 10, "review": "Updated review text: An undeniable masterpiece from Christopher Nolan."},
    )
    assert c1_update_res.status_code == 200
    assert c1_update_res.json()["rating"] == 10

    # 10. Critic 1 deletes their OWN review -> 200 OK
    c1_del_res = await c1_client.delete(f"/api/v1/reviews/{review_id}")
    assert c1_del_res.status_code == 200
    assert c1_del_res.json()["success"] is True


@pytest.mark.asyncio
async def test_viewer_permissions_and_restrictions(
    admin_client: AsyncClient,
    viewer_client: AsyncClient,
):
    """
    Viewers:
    - CAN read film catalog (200 OK)
    - CAN read film detail (200 OK)
    - CAN read film reviews (200 OK)
    - CAN read film average rating (200 OK)
    - CANNOT create films (403 Forbidden)
    - CANNOT update films (403 Forbidden)
    - CANNOT delete films (403 Forbidden)
    - CANNOT create reviews (403 Forbidden)
    - CANNOT update reviews (403 Forbidden)
    - CANNOT delete reviews (403 Forbidden)
    - CANNOT access Admin stats (403 Forbidden)
    """
    # 1. Admin sets up a film and review
    film_res = await admin_client.post(
        "/api/v1/films",
        json={
            "title": "Dunkirk",
            "director": "Christopher Nolan",
            "releaseYear": 2017,
            "genre": "War",
            "description": "Allied soldiers from Belgium, the British Empire, and France are surrounded by the German Army.",
        },
    )
    assert film_res.status_code == 201
    film_id = film_res.json()["id"]

    rev_res = await admin_client.post(
        f"/api/v1/films/{film_id}/reviews",
        json={
            "film_id": film_id,
            "rating": 9,
            "review": "A masterclass in tension, sound design, and visceral cinematic realism on screen.",
            "reviewer_display_name": "Lead Critic",
        },
    )
    assert rev_res.status_code == 201
    review_id = rev_res.json()["id"]

    # 2. Viewer CAN read films
    films_list_res = await viewer_client.get("/api/v1/films")
    assert films_list_res.status_code == 200
    assert any(f["id"] == film_id for f in films_list_res.json())

    # 3. Viewer CAN read film detail
    film_detail_res = await viewer_client.get(f"/api/v1/films/{film_id}")
    assert film_detail_res.status_code == 200
    assert film_detail_res.json()["title"] == "Dunkirk"

    # 4. Viewer CAN read reviews
    reviews_res = await viewer_client.get(f"/api/v1/films/{film_id}/reviews")
    assert reviews_res.status_code == 200
    assert len(reviews_res.json()) >= 1

    # 5. Viewer CAN read average rating
    avg_res = await viewer_client.get(f"/api/v1/films/{film_id}/reviews/average")
    assert avg_res.status_code == 200
    assert avg_res.json()["average_rating"] is not None

    # 6. Viewer CANNOT create film -> 403 Forbidden
    create_film_res = await viewer_client.post(
        "/api/v1/films",
        json={
            "title": "Illegal Viewer Film",
            "director": "Viewer",
            "releaseYear": 2023,
            "genre": "Drama",
            "description": "Should be rejected.",
        },
    )
    assert create_film_res.status_code == 403

    # 7. Viewer CANNOT create review -> 403 Forbidden
    create_rev_res = await viewer_client.post(
        f"/api/v1/films/{film_id}/reviews",
        json={
            "film_id": film_id,
            "rating": 5,
            "review": "Viewers are not allowed to submit reviews on this platform.",
            "reviewer_display_name": "Viewer Alex",
        },
    )
    assert create_rev_res.status_code == 403

    # 8. Viewer CANNOT update review -> 403 Forbidden
    update_rev_res = await viewer_client.patch(
        f"/api/v1/reviews/{review_id}",
        json={"rating": 1, "review": "Viewer attempt to alter review content."},
    )
    assert update_rev_res.status_code == 403

    # 9. Viewer CANNOT delete review -> 403 Forbidden
    del_rev_res = await viewer_client.delete(f"/api/v1/reviews/{review_id}")
    assert del_rev_res.status_code == 403

    # 10. Viewer CANNOT delete film -> 403 Forbidden
    del_film_res = await viewer_client.delete(f"/api/v1/films/{film_id}")
    assert del_film_res.status_code == 403

    # 11. Viewer CANNOT access admin stats -> 403 Forbidden
    stats_res = await viewer_client.get("/api/v1/admin/stats")
    assert stats_res.status_code == 403


@pytest.mark.asyncio
async def test_disallow_admin_account_creation_on_registration(client: AsyncClient):
    """
    Public registration prevents creation of admin accounts.
    Attempting to register with role='admin' must be rejected (422 Unprocessable or 403 Forbidden).
    Only the single pre-seeded administrator exists.
    """
    reg_payload = {
        "username": "rogue_admin",
        "email": "rogue@admin.com",
        "password": "Password123!",
        "role": "admin",
    }
    res = await client.post("/api/v1/register", json=reg_payload)
    assert res.status_code in (403, 422)

