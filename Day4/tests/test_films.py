from __future__ import annotations

import uuid
from httpx import AsyncClient
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.film import Film
from tests.helpers import get_user_headers


@pytest.mark.integration
async def test_film_crud_lifecycle(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """
    Complete Film CRUD Lifecycle Integration Test
    Scenario:
    Admin:
      Create film
      ↓
      Fetch film
      ↓
      Update title
      ↓
      Verify persisted update
      ↓
    Viewer attempts delete
      ↓
      403 Forbidden
      ↓
    Admin deletes film
      ↓
    List endpoint confirms film no longer exists

    Assertions after every step:
    - status codes
    - response body
    - database persistence
    - role enforcement
    """
    # -------------------------------------------------------------------------
    # Arrange: Setup admin and viewer authenticated credentials
    # -------------------------------------------------------------------------
    admin_headers = await get_user_headers(
        client=client,
        session=db_session,
        role="admin",
        username="admin_nolan",
    )
    viewer_headers = await get_user_headers(
        client=client,
        session=db_session,
        role="viewer",
        username="viewer_cinephile",
    )

    film_payload = {
        "title": "Oppenheimer",
        "director": "Christopher Nolan",
        "release_year": 2023,
        "genre": "Biography",
        "description": "The story of American scientist J. Robert Oppenheimer and the Manhattan Project.",
    }

    # -------------------------------------------------------------------------
    # Step 1: Admin Creates Film
    # -------------------------------------------------------------------------
    create_res = await client.post("/films", json=film_payload, headers=admin_headers)

    # Assert Step 1: Status code and response body
    assert create_res.status_code == 201, f"Create film failed: {create_res.text}"
    created_data = create_res.json()
    assert "id" in created_data
    film_id = uuid.UUID(created_data["id"])
    assert created_data["title"] == film_payload["title"]
    assert created_data["director"] == film_payload["director"]
    assert (created_data.get("release_year") or created_data.get("releaseYear")) == film_payload["release_year"]
    assert created_data["genre"] == film_payload["genre"]

    # Assert Step 1: Database persistence
    db_film = (await db_session.execute(select(Film).where(Film.id == film_id))).scalar_one_or_none()
    assert db_film is not None, "Film was not persisted to the database"
    assert db_film.title == film_payload["title"]
    assert db_film.director == film_payload["director"]
    assert db_film.is_active is True

    # -------------------------------------------------------------------------
    # Step 2: Fetch Film
    # -------------------------------------------------------------------------
    fetch_res = await client.get(f"/films/{film_id}", headers=admin_headers)

    # Assert Step 2: Status code and fetched response body
    assert fetch_res.status_code == 200, f"Fetch film failed: {fetch_res.text}"
    fetched_data = fetch_res.json()
    assert fetched_data["id"] == str(film_id)
    assert fetched_data["title"] == film_payload["title"]
    assert fetched_data["director"] == film_payload["director"]

    # -------------------------------------------------------------------------
    # Step 3: Admin Updates Title
    # -------------------------------------------------------------------------
    updated_title = "Oppenheimer: The Director's Cut"
    update_payload = {"title": updated_title}
    update_res = await client.patch(
        f"/films/{film_id}",
        json=update_payload,
        headers=admin_headers,
    )

    # Assert Step 3: Status code and updated response body
    assert update_res.status_code == 200, f"Update film failed: {update_res.text}"
    updated_data = update_res.json()
    assert updated_data["id"] == str(film_id)
    assert updated_data["title"] == updated_title

    # -------------------------------------------------------------------------
    # Step 4: Verify Persisted Update (via API fetch & direct database read)
    # -------------------------------------------------------------------------
    verify_res = await client.get(f"/films/{film_id}", headers=admin_headers)
    assert verify_res.status_code == 200
    assert verify_res.json()["title"] == updated_title

    # Assert Step 4: Database persistence of update
    db_film_updated = (await db_session.execute(select(Film).where(Film.id == film_id))).scalar_one_or_none()
    assert db_film_updated is not None
    assert db_film_updated.title == updated_title

    # -------------------------------------------------------------------------
    # Step 5: Viewer Attempts Delete -> 403 Forbidden
    # -------------------------------------------------------------------------
    viewer_delete_res = await client.delete(
        f"/films/{film_id}",
        headers=viewer_headers,
    )

    # Assert Step 5: Role enforcement status and rejection
    assert viewer_delete_res.status_code == 403, (
        f"Expected 403 Forbidden for viewer delete, got {viewer_delete_res.status_code}"
    )

    # Assert Step 5: Database confirms film is still active and was NOT deleted
    db_film_after_viewer = (await db_session.execute(select(Film).where(Film.id == film_id))).scalar_one_or_none()
    assert db_film_after_viewer is not None
    assert db_film_after_viewer.is_active is True

    # -------------------------------------------------------------------------
    # Step 6: Admin Deletes Film -> 200 OK
    # -------------------------------------------------------------------------
    admin_delete_res = await client.delete(
        f"/films/{film_id}",
        headers=admin_headers,
    )

    # Assert Step 6: Status code and response message
    assert admin_delete_res.status_code == 200, f"Admin delete failed: {admin_delete_res.text}"
    del_data = admin_delete_res.json()
    assert del_data.get("success") is True or "deleted" in del_data.get("message", "").lower()

    # Assert Step 6: Database confirms soft-delete (is_active is False)
    db_film_after_admin = (await db_session.execute(select(Film).where(Film.id == film_id))).scalar_one_or_none()
    assert db_film_after_admin is not None
    assert db_film_after_admin.is_active is False

    # -------------------------------------------------------------------------
    # Step 7: List Endpoint Confirms Film No Longer Exists
    # -------------------------------------------------------------------------
    list_res = await client.get("/films", headers=admin_headers)
    assert list_res.status_code == 200
    active_items = list_res.json().get("items", [])
    active_film_ids = [item["id"] for item in active_items]
    assert str(film_id) not in active_film_ids, "Soft-deleted film unexpectedly appeared in active film list"

    # Direct fetch of soft-deleted film should return 404 Not Found
    fetch_deleted_res = await client.get(f"/films/{film_id}", headers=admin_headers)
    assert fetch_deleted_res.status_code == 404


@pytest.mark.integration
async def test_viewer_cannot_create_film(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Verify that a viewer role receives 403 Forbidden when attempting to create a film."""
    viewer_headers = await get_user_headers(client=client, session=db_session, role="viewer")
    payload = {
        "title": "Forbidden Movie",
        "director": "Unauthorized Director",
        "release_year": 2024,
        "genre": "Drama",
        "description": "This should not be created.",
    }
    response = await client.post("/films", json=payload, headers=viewer_headers)
    assert response.status_code == 403


@pytest.mark.integration
async def test_critic_cannot_create_film(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Verify that a critic role receives 403 Forbidden when attempting to create a film (admin only)."""
    critic_headers = await get_user_headers(client=client, session=db_session, role="critic")
    payload = {
        "title": "Critic Attempt Movie",
        "director": "Unauthorized Critic",
        "release_year": 2024,
        "genre": "Sci-Fi",
        "description": "Critics cannot create films.",
    }
    response = await client.post("/films", json=payload, headers=critic_headers)
    assert response.status_code == 403


@pytest.mark.integration
async def test_viewer_cannot_update_film(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Verify that a viewer role receives 403 Forbidden when attempting to update a film."""
    admin_headers = await get_user_headers(client=client, session=db_session, role="admin")
    viewer_headers = await get_user_headers(client=client, session=db_session, role="viewer")

    # Create film with admin
    create_res = await client.post(
        "/films",
        json={
            "title": "Original Title",
            "director": "Director One",
            "release_year": 2021,
            "genre": "Action",
        },
        headers=admin_headers,
    )
    assert create_res.status_code == 201
    film_id = create_res.json()["id"]

    # Attempt update with viewer
    update_res = await client.patch(
        f"/films/{film_id}",
        json={"title": "Hacked Title"},
        headers=viewer_headers,
    )
    assert update_res.status_code == 403


@pytest.mark.integration
async def test_get_nonexistent_film(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Verify that requesting a nonexistent film returns 404 Not Found."""
    headers = await get_user_headers(client=client, session=db_session, role="viewer")
    fake_id = uuid.uuid4()
    response = await client.get(f"/films/{fake_id}", headers=headers)
    assert response.status_code == 404
