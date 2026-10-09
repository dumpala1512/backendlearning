from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import UserNotFoundError
from app.dependencies import get_current_user, get_db, get_user_service, require_role
from app.schemas.user import AdminStatsResponse, AuthenticatedUser, UserResponse
from app.services.user_service import UserService

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/users/me", response_model=UserResponse, tags=["Users"], summary="Get current user profile")
@router.get("/me", response_model=UserResponse, include_in_schema=False)
async def get_current_user_profile(
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Get profile information for the authenticated current user from PostgreSQL."""
    try:
        user = await service.get_by_id(session=db, user_id=current_user.id)
        return UserResponse.model_validate(user)
    except UserNotFoundError:
        return UserResponse(
            id=current_user.id,
            username=current_user.username,
            email=current_user.email or f"{current_user.username}@example.com",
            role=current_user.role,
        )


@router.get("/users", response_model=list[UserResponse], tags=["Users"], summary="List all users")
async def list_all_users(
    service: UserService = Depends(get_user_service),
    db: AsyncSession = Depends(get_db),
) -> list[UserResponse]:
    """Get a list of all registered users from PostgreSQL."""
    users = await service.list_users(session=db, limit=50)
    return [UserResponse.model_validate(u) for u in users]


@router.get(
    "/admin/stats",
    response_model=AdminStatsResponse,
    tags=["Admin"],
    summary="Get platform statistics",
    dependencies=[Depends(get_current_user), Depends(require_role("admin"))],
)
@router.get(
    "/users/admin/stats",
    response_model=AdminStatsResponse,
    tags=["Admin"],
    include_in_schema=False,
    dependencies=[Depends(get_current_user), Depends(require_role("admin"))],
)
async def get_admin_statistics(
    current_user: AuthenticatedUser = Depends(require_role("admin")),
    service: UserService = Depends(get_user_service),
    db: AsyncSession = Depends(get_db),
) -> AdminStatsResponse:
    """Get platform-wide metrics and stats directly via DAO counts."""
    stats = await service.get_admin_stats(session=db)
    return AdminStatsResponse(
        total_users=int(stats["total_users"]),
        total_films=int(stats["total_films"]),
        total_reviews=int(stats["total_reviews"]),
        overall_average_rating=stats["overall_average_rating"],
        top_reviewer_username=stats["top_reviewer_username"],
        uptime_status=str(stats["uptime_status"]),
    )
