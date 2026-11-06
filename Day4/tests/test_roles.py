from __future__ import annotations

import uuid
from httpx import AsyncClient
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dao.film_dao import FilmDAO
from app.models.review import Review
from tests.helpers import get_user_headers


@pytest.mark.integration
class TestRoleEnforcementReviewEndpoints:
    """
    Endpoint Pair 1: Create Review & Delete Review
    - Allowed Case: Correct role (Critic for create, Admin for delete)
    - Forbidden Case: Wrong role (Viewer rejected with 403, non-author Critic rejected with 403)
    """

    async def _create_test_film(self, session: AsyncSession) -> uuid.UUID:
        film_dao = FilmDAO()
        film = await film_dao.create(
            session=session,
            title="The Grand Budapest Hotel",
            director="Wes Anderson",
            release_year=2014,
            genre="Comedy",
            description="Adventures of Gustave H at a famous European hotel.",
        )
        return film.id

    async def test_create_review_allowed_for_critic(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """Allowed Case: Critic creates a review -> 201 Created."""
        # Arrange
        film_id = await self._create_test_film(db_session)
        critic_headers = await get_user_headers(
            client=client,
            session=db_session,
            role="critic",
            username="ebert_official",
        )
        payload = {
            "film_id": str(film_id),
            "rating": 9,
            "review": "A delightful cinematic confection with exquisite design.",
            "reviewer_display_name": "Ebert",
        }

        # Act
        response = await client.post(
            f"/films/{film_id}/reviews",
            json=payload,
            headers=critic_headers,
        )

        # Assert: Allowed status & schema
        assert response.status_code == 201, f"Expected 201 Created, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["film_id"] == str(film_id)
        assert data["rating"] == 9
        assert data["review"] == payload["review"]
        assert "id" in data

        # Assert: Database persistence
        review_id = uuid.UUID(data["id"])
        persisted = (await db_session.execute(select(Review).where(Review.id == review_id))).scalar_one_or_none()
        assert persisted is not None
        assert persisted.rating == 9

    async def test_create_review_forbidden_for_viewer(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """Forbidden Case: Viewer attempts to create a review -> 403 Forbidden."""
        # Arrange
        film_id = await self._create_test_film(db_session)
        viewer_headers = await get_user_headers(
            client=client,
            session=db_session,
            role="viewer",
            username="casual_viewer_tom",
        )
        payload = {
            "film_id": str(film_id),
            "rating": 8,
            "review": "Great movie, really enjoyed the colors.",
            "reviewer_display_name": "Tom",
        }

        # Act
        response = await client.post(
            f"/films/{film_id}/reviews",
            json=payload,
            headers=viewer_headers,
        )

        # Assert: Rejection status & error body
        assert response.status_code == 403, f"Expected 403 Forbidden, got {response.status_code}"
        err = response.json()
        assert "error" in err or "message" in err or "detail" in err
        err_str = str(err).lower()
        assert "forbidden" in err_str or "role" in err_str or "permission" in err_str

    async def test_delete_review_allowed_for_admin(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """Allowed Case: Admin deletes any review -> 200 OK."""
        # Arrange: Critic creates a review first
        film_id = await self._create_test_film(db_session)
        critic_headers = await get_user_headers(
            client=client,
            session=db_session,
            role="critic",
            username="critic_for_delete",
        )
        create_res = await client.post(
            f"/films/{film_id}/reviews",
            json={
                "film_id": str(film_id),
                "rating": 7,
                "review": "Adequate filmmaking with impressive set design and solid pacing overall.",
                "reviewer_display_name": "Critic D",
            },
            headers=critic_headers,
        )
        assert create_res.status_code == 201, f"Create review failed: {create_res.text}"
        review_id = create_res.json()["id"]

        # Act: Admin deletes the review
        admin_headers = await get_user_headers(
            client=client,
            session=db_session,
            role="admin",
            username="admin_cleaner",
        )
        response = await client.delete(f"/reviews/{review_id}", headers=admin_headers)

        # Assert: Allowed status & persistence removal
        assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}: {response.text}"
        persisted = (await db_session.execute(select(Review).where(Review.id == uuid.UUID(review_id)))).scalar_one_or_none()
        assert persisted is None

    async def test_delete_review_forbidden_for_viewer(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """Forbidden Case: Viewer attempts to delete a review -> 403 Forbidden."""
        # Arrange: Critic creates a review
        film_id = await self._create_test_film(db_session)
        critic_headers = await get_user_headers(
            client=client,
            session=db_session,
            role="critic",
            username="critic_author",
        )
        create_res = await client.post(
            f"/films/{film_id}/reviews",
            json={
                "film_id": str(film_id),
                "rating": 10,
                "review": "Absolute cinematic masterpiece with breathtaking cinematography and script.",
                "reviewer_display_name": "Critic A",
            },
            headers=critic_headers,
        )
        assert create_res.status_code == 201, f"Create review failed: {create_res.text}"
        review_id = create_res.json()["id"]

        # Act: Viewer attempts to delete
        viewer_headers = await get_user_headers(
            client=client,
            session=db_session,
            role="viewer",
            username="malicious_viewer",
        )
        response = await client.delete(f"/reviews/{review_id}", headers=viewer_headers)

        # Assert: Rejection status & error body
        assert response.status_code == 403
        err = response.json()
        assert "error" in err or "message" in err or "detail" in err


@pytest.mark.integration
class TestRoleEnforcementAdminStatsEndpoint:
    """
    Endpoint Pair 2: Admin Dashboard / Platform Statistics (GET /admin/stats)
    - Allowed Case: Admin role gets 200 OK with statistics
    - Forbidden Case: Viewer & Critic roles rejected with 403 Forbidden
    """

    async def test_admin_stats_allowed_for_admin(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """Allowed Case: Admin accesses stats endpoint -> 200 OK with metrics."""
        # Arrange
        admin_headers = await get_user_headers(
            client=client,
            session=db_session,
            role="admin",
            username="stats_admin_boss",
        )

        # Act
        response = await client.get("/admin/stats", headers=admin_headers)

        # Assert: Status 200 and expected schema shape
        assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}: {response.text}"
        data = response.json()
        assert "total_users" in data
        assert "total_films" in data
        assert "total_reviews" in data
        assert "uptime_status" in data
        assert isinstance(data["total_users"], int)
        assert isinstance(data["total_films"], int)
        assert isinstance(data["total_reviews"], int)

    async def test_admin_stats_forbidden_for_viewer(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """Forbidden Case: Viewer attempts to access admin stats -> 403 Forbidden."""
        # Arrange
        viewer_headers = await get_user_headers(
            client=client,
            session=db_session,
            role="viewer",
            username="nosy_viewer",
        )

        # Act
        response = await client.get("/admin/stats", headers=viewer_headers)

        # Assert: Rejection status 403
        assert response.status_code == 403
        err = response.json()
        assert "error" in err or "message" in err or "detail" in err

    async def test_admin_stats_forbidden_for_critic(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """Forbidden Case: Critic attempts to access admin stats -> 403 Forbidden."""
        # Arrange
        critic_headers = await get_user_headers(
            client=client,
            session=db_session,
            role="critic",
            username="curious_critic",
        )

        # Act
        response = await client.get("/admin/stats", headers=critic_headers)

        # Assert: Rejection status 403
        assert response.status_code == 403
        err = response.json()
        assert "error" in err or "message" in err or "detail" in err
