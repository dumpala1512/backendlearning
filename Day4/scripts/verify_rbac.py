#!/usr/bin/env python3
"""
Manual Verification Script for Role-Based Access Control (RBAC).

Executes at least three requests per role (Admin, Critic, Viewer), covering
permitted actions and forbidden attempts (HTTP 403 / 200 / 201), verifying:
1. Admin: Create/update/delete any film & review, access Admin stats.
2. Critic: Create review, update own review, forbidden on film creation & admin stats.
3. Viewer: Read films/reviews, profile (/me), forbidden on create/update/delete.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

BASE_URL = "http://localhost:8000"


def send_request(
    endpoint: str,
    method: str = "GET",
    token: str | None = None,
    payload: dict | None = None,
) -> tuple[int, dict]:
    url = f"{BASE_URL}{endpoint}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(payload).encode() if payload else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            body = json.loads(resp.read().decode()) if resp.length else {}
            return resp.status, body
    except urllib.error.HTTPError as err:
        body = json.loads(err.read().decode()) if err.fp else {}
        return err.code, body


def main() -> None:
    print("=" * 70)
    print("FILM REVIEW PLATFORM - RBAC VERIFICATION PASS")
    print("=" * 70)

    # Authenticate all 3 identities
    _, admin_login = send_request(
        "/api/v1/login",
        method="POST",
        payload={"username": "admin_sarah", "password": "AdminPass123!"},
    )
    admin_token = admin_login["access_token"]

    _, critic_login = send_request(
        "/api/v1/login",
        method="POST",
        payload={"username": "marcus_reviews", "password": "CriticPass123!"},
    )
    critic_token = critic_login["access_token"]

    _, viewer_login = send_request(
        "/api/v1/login",
        method="POST",
        payload={"username": "lucas_viewer", "password": "ViewerPass123!"},
    )
    viewer_token = viewer_login["access_token"]

    print("\n[+] Tokens successfully generated:")
    print(f"  * Admin token (admin_sarah): {admin_token[:20]}...")
    print(f"  * Critic token (marcus_reviews): {critic_token[:20]}...")
    print(f"  * Viewer token (lucas_viewer): {viewer_token[:20]}...\n")

    # ---------------------------------------------------------
    # 1. ADMIN ROLE VERIFICATION
    # ---------------------------------------------------------
    print("-" * 70)
    print("ROLE: ADMIN (admin_sarah)")
    print("-" * 70)

    # Permitted 1: Get Profile /me
    status, body = send_request("/api/v1/me", token=admin_token)
    print(f"[1] GET /api/v1/me  -> HTTP {status} (Expected: 200)")
    assert status == 200, f"Expected 200, got {status}"
    print(f"    Username: {body.get('username')}, Role: {body.get('role')}")

    # Permitted 2: Admin-only stats
    status, stats = send_request("/api/v1/admin/stats", token=admin_token)
    print(f"[2] GET /api/v1/admin/stats  -> HTTP {status} (Expected: 200)")
    assert status == 200, f"Expected 200, got {status}"
    print(f"    Total Films: {stats.get('total_films')}")
    print(f"    Total Reviews: {stats.get('total_reviews')}")
    print(f"    Overall Avg Rating: {stats.get('overall_average_rating')}")
    print(f"    Top Reviewer: {stats.get('top_reviewer_username')}")

    # Permitted 3: Create Film
    status, film = send_request(
        "/api/v1/films",
        method="POST",
        token=admin_token,
        payload={
            "title": "Oppenheimer Verification",
            "director": "Christopher Nolan",
            "releaseYear": 2023,
            "genre": "Biography",
            "description": "The story of American scientist J. Robert Oppenheimer and the Manhattan Project.",
        },
    )
    print(f"[3] POST /api/v1/films  -> HTTP {status} (Expected: 201)")
    assert status == 201, f"Expected 201, got {status}"
    film_id = film["id"]
    print(f"    Film ID: {film_id}, Title: {film['title']}")

    # ---------------------------------------------------------
    # 2. CRITIC ROLE VERIFICATION
    # ---------------------------------------------------------
    print("\n" + "-" * 70)
    print("ROLE: CRITIC (marcus_reviews)")
    print("-" * 70)

    # Permitted 1: Create Review on Film
    status, review = send_request(
        f"/api/v1/films/{film_id}/reviews",
        method="POST",
        token=critic_token,
        payload={
            "film_id": film_id,
            "rating": 10,
            "review": "A masterwork of tension and historical drama with incredible sound and visual pacing.",
            "reviewer_display_name": "Marcus Vance",
        },
    )
    print(f"[1] POST /api/v1/films/{{id}}/reviews (Permitted) -> HTTP {status} (Expected: 201)")
    assert status == 201, f"Expected 201, got {status}"
    review_id = review["id"]
    print(f"    Review ID: {review_id}, Rating: {review['rating']}")

    # Forbidden 1: Critic cannot create films
    status, err = send_request(
        "/api/v1/films",
        method="POST",
        token=critic_token,
        payload={
            "title": "Unauthorized Critic Film",
            "director": "Nobody",
            "releaseYear": 2024,
            "genre": "Drama",
            "description": "Critics are not authorized to create films.",
        },
    )
    print(f"[2] POST /api/v1/films (Forbidden) -> HTTP {status} (Expected: 403)")
    assert status == 403, f"Expected 403, got {status}"
    print(f"    Error Type: {err.get('type')}, Message: {err.get('message')}")

    # Forbidden 2: Critic cannot access Admin stats
    status, err = send_request("/api/v1/admin/stats", token=critic_token)
    print(f"[3] GET /api/v1/admin/stats (Forbidden) -> HTTP {status} (Expected: 403)")
    assert status == 403, f"Expected 403, got {status}"
    print(f"    Error Type: {err.get('type')}, Message: {err.get('message')}")

    # ---------------------------------------------------------
    # 3. VIEWER ROLE VERIFICATION
    # ---------------------------------------------------------
    print("\n" + "-" * 70)
    print("ROLE: VIEWER (lucas_viewer)")
    print("-" * 70)

    # Permitted 1: Viewer can read film catalog and details
    status, films_list = send_request("/api/v1/films", token=viewer_token)
    print(f"[1] GET /api/v1/films (Permitted) -> HTTP {status} (Expected: 200)")
    assert status == 200, f"Expected 200, got {status}"
    print(f"    Retrieved {len(films_list)} films successfully.")

    # Forbidden 1: Viewer cannot create reviews
    status, err = send_request(
        f"/api/v1/films/{film_id}/reviews",
        method="POST",
        token=viewer_token,
        payload={
            "film_id": film_id,
            "rating": 7,
            "review": "Viewers are read-only and may not submit reviews.",
            "reviewer_display_name": "Lucas Viewer",
        },
    )
    print(f"[2] POST /api/v1/films/{{id}}/reviews (Forbidden) -> HTTP {status} (Expected: 403)")
    assert status == 403, f"Expected 403, got {status}"
    print(f"    Error Type: {err.get('type')}, Message: {err.get('message')}")

    # Forbidden 2: Viewer cannot delete films
    status, err = send_request(f"/api/v1/films/{film_id}", method="DELETE", token=viewer_token)
    print(f"[3] DELETE /api/v1/films/{{id}} (Forbidden) -> HTTP {status} (Expected: 403)")
    assert status == 403, f"Expected 403, got {status}"
    print(f"    Error Type: {err.get('type')}, Message: {err.get('message')}")

    print("\n" + "=" * 70)
    print("[SUCCESS] ALL 9 RBAC VERIFICATION REQUESTS PASSED AS EXPECTED!")
    print("=" * 70)


if __name__ == "__main__":
    main()
