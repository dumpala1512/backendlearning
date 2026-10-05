from __future__ import annotations

import uuid
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_complete_film_route_to_database_flow(client: AsyncClient):
    # 1. Create a film via POST /api/v1/films
    create_payload = {
        "title": "The Matrix",
        "director": "Lana & Lilly Wachowski",
        "releaseYear": 1999,
        "genre": "Sci-Fi",
        "description": "A computer hacker learns from mysterious rebels about the true nature of his reality.",
    }
    create_res = await client.post("/api/v1/films", json=create_payload)
    assert create_res.status_code == 201
    assert "x-trace-id" in create_res.headers
    assert len(create_res.headers["x-trace-id"]) > 0
    created_film = create_res.json()
    assert created_film["title"] == "The Matrix"
    assert created_film["id"] is not None
    film_id = created_film["id"]
    # Check that film_id is a valid UUID string
    uuid.UUID(film_id)

    # 2. Retrieve the film via GET /api/v1/films/{id}
    get_res = await client.get(f"/api/v1/films/{film_id}")
    assert get_res.status_code == 200
    assert get_res.json()["director"] == "Lana & Lilly Wachowski"

    # 3. List films via GET /api/v1/films with filtering
    list_res = await client.get("/api/v1/films?genre=Sci-Fi")
    assert list_res.status_code == 200
    films = list_res.json()
    assert len(films) >= 1
    assert any(f["id"] == film_id for f in films)

    # 4. Partially update film via PATCH /api/v1/films/{id}
    update_res = await client.patch(
        f"/api/v1/films/{film_id}",
        json={"description": "Updated cyberpunk classic synopsis."},
    )
    assert update_res.status_code == 200
    assert update_res.json()["description"] == "Updated cyberpunk classic synopsis."

    # 5. Soft delete film via DELETE /api/v1/films/{id}
    del_res = await client.delete(f"/api/v1/films/{film_id}")
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True

    # 6. Deleted film is no longer accessible via GET /api/v1/films/{id} -> 404
    deleted_get_res = await client.get(f"/api/v1/films/{film_id}")
    assert deleted_get_res.status_code == 404

    # 7. Deleted film is excluded from GET /api/v1/films listing
    after_delete_list = await client.get("/api/v1/films")
    assert after_delete_list.status_code == 200
    assert all(f["id"] != film_id for f in after_delete_list.json())

    # 8. Admin stats reflects the deleted film count
    stats_res = await client.get("/api/v1/users/admin/stats")
    assert stats_res.status_code == 200
    assert stats_res.json()["total_films"] == 0

    # 9. Requesting non-existent film triggers domain exception handler -> 404
    missing_res = await client.get(f"/api/v1/films/{uuid.uuid4()}")
    assert missing_res.status_code == 404
    assert "not found" in missing_res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_complete_review_route_to_database_flow(client: AsyncClient):
    # 1. Create a film to attach reviews to
    film_res = await client.post(
        "/api/v1/films",
        json={
            "title": "Parasite",
            "director": "Bong Joon-ho",
            "releaseYear": 2019,
            "genre": "Thriller",
            "description": "Greed and class discrimination threaten the newly formed symbiotic relationship.",
        },
    )
    assert film_res.status_code == 201
    film_id = film_res.json()["id"]

    # 2. Add review via POST /api/v1/films/{id}/reviews
    review_res = await client.post(
        f"/api/v1/films/{film_id}/reviews",
        json={
            "film_id": film_id,
            "rating": 10,
            "review": "A masterfully crafted social thriller with shocking twists and turns throughout the movie.",
            "reviewer_display_name": "Cinephile Extraordinaire",
        },
    )
    assert review_res.status_code == 201
    created_review = review_res.json()
    assert created_review["rating"] == 10
    review_id = created_review["id"]
    uuid.UUID(review_id)

    # 3. Add second review
    review_res2 = await client.post(
        f"/api/v1/films/{film_id}/reviews",
        json={
            "film_id": film_id,
            "rating": 8,
            "review": "Brilliant dark humor and intense cinematography that keeps you on the edge of your seat.",
            "reviewer_display_name": "Second Critic",
        },
    )
    assert review_res2.status_code == 201

    # 4. Get reviews for the film
    list_res = await client.get(f"/api/v1/films/{film_id}/reviews")
    assert list_res.status_code == 200
    reviews = list_res.json()
    assert len(reviews) == 2
    # Verify newest first ordering
    assert reviews[0]["rating"] == 8
    assert reviews[1]["rating"] == 10

    # 5. Get average rating
    avg_res = await client.get(f"/api/v1/films/{film_id}/reviews/average")
    assert avg_res.status_code == 200
    assert avg_res.json()["average_rating"] == 9.0

    # 6. Delete a review
    delete_res = await client.delete(f"/api/v1/reviews/{review_id}")
    assert delete_res.status_code == 200
    assert delete_res.json()["success"] is True


@pytest.mark.asyncio
async def test_soft_delete_affects_all_routes_and_admin_stats(client: AsyncClient):
    """
    Verify that soft deleting a film:
    1. Decrements total_films in admin stats
    2. Excludes it from GET /api/v1/films
    3. Causes GET /api/v1/films/{id} to return 404
    4. Causes GET /api/v1/films/{id}/reviews to return 404
    5. Causes GET /api/v1/films/{id}/reviews/average to return 404
    6. Prevents POST /api/v1/films/{id}/reviews (returns 404)
    7. Prevents PATCH /api/v1/films/{id} (returns 404)
    8. Prevents subsequent DELETE /api/v1/films/{id} (returns 404)
    """
    # 1. Create a film
    create_res = await client.post(
        "/api/v1/films",
        json={
            "title": "Avatar",
            "director": "James Cameron",
            "releaseYear": 2009,
            "genre": "Sci-Fi",
            "description": "A paraplegic Marine dispatched to the moon Pandora on a unique mission.",
        },
    )
    assert create_res.status_code == 201
    film_id = create_res.json()["id"]

    # 2. Add a review for this film
    rev_res = await client.post(
        f"/api/v1/films/{film_id}/reviews",
        json={
            "film_id": film_id,
            "rating": 9,
            "review": "Groundbreaking visual effects and immersive world building in 3D.",
            "reviewer_display_name": "SciFi Buff",
        },
    )
    assert rev_res.status_code == 201

    # 3. Check admin stats before deletion
    stats_before = await client.get("/api/v1/admin/stats")
    assert stats_before.status_code == 200
    films_count_before = stats_before.json()["total_films"]
    reviews_count_before = stats_before.json()["total_reviews"]
    assert films_count_before >= 1
    assert reviews_count_before >= 1

    # 4. Soft delete the film
    del_res = await client.delete(f"/api/v1/films/{film_id}")
    assert del_res.status_code == 200

    # 5. Check admin stats after deletion: both total_films and total_reviews decrease
    stats_after = await client.get("/api/v1/admin/stats")
    assert stats_after.status_code == 200
    assert stats_after.json()["total_films"] == films_count_before - 1
    assert stats_after.json()["total_reviews"] == reviews_count_before - 1

    # 6. GET /api/v1/films: excluded
    list_res = await client.get("/api/v1/films")
    assert list_res.status_code == 200
    assert all(f["id"] != film_id for f in list_res.json())

    # 7. GET /api/v1/films/{id}: returns 404
    get_res = await client.get(f"/api/v1/films/{film_id}")
    assert get_res.status_code == 404

    # 8. GET /api/v1/films/{id}/reviews: returns 404
    reviews_res = await client.get(f"/api/v1/films/{film_id}/reviews")
    assert reviews_res.status_code == 404

    # 9. GET /api/v1/films/{id}/reviews/average: returns 404
    avg_res = await client.get(f"/api/v1/films/{film_id}/reviews/average")
    assert avg_res.status_code == 404

    # 10. POST /api/v1/films/{id}/reviews: returns 404
    add_rev_res = await client.post(
        f"/api/v1/films/{film_id}/reviews",
        json={
            "film_id": film_id,
            "rating": 7,
            "review": "Trying to add review to a deleted film should fail with not found.",
        },
    )
    assert add_rev_res.status_code == 404

    # 11. PATCH /api/v1/films/{id}: returns 404
    patch_res = await client.patch(
        f"/api/v1/films/{film_id}",
        json={"title": "Avatar 2"},
    )
    assert patch_res.status_code == 404

    # 12. Subsequent DELETE /api/v1/films/{id}: returns 404
    re_del_res = await client.delete(f"/api/v1/films/{film_id}")
    assert re_del_res.status_code == 404
