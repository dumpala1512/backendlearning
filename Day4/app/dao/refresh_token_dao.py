from __future__ import annotations

from datetime import datetime
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.refresh_token import RefreshToken


class RefreshTokenDAO:
    """
    Data Access Object for RefreshToken entities.
    Encapsulates all asynchronous database operations for refresh token validation,
    issuance, and replay prevention.
    """

    async def create(
        self,
        session: AsyncSession,
        token: str,
        jti: str,
        user_id: uuid.UUID,
        expires_at: datetime,
    ) -> RefreshToken:
        """Insert and persist a new refresh token record."""
        record = RefreshToken(
            token=token,
            jti=jti,
            user_id=user_id,
            expires_at=expires_at,
            is_used=False,
            is_revoked=False,
        )
        session.add(record)
        await session.commit()
        await session.refresh(record)
        return record

    async def get_by_jti(
        self,
        session: AsyncSession,
        jti: str,
    ) -> RefreshToken | None:
        """Find a refresh token by unique JTI."""
        query = select(RefreshToken).where(RefreshToken.jti == jti)
        result = await session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_token(
        self,
        session: AsyncSession,
        token: str,
    ) -> RefreshToken | None:
        """Find a refresh token by raw token string."""
        query = select(RefreshToken).where(RefreshToken.token == token)
        result = await session.execute(query)
        return result.scalar_one_or_none()

    async def mark_as_used(
        self,
        session: AsyncSession,
        record: RefreshToken,
    ) -> RefreshToken:
        """Mark a refresh token as consumed (used)."""
        record.is_used = True
        session.add(record)
        await session.commit()
        await session.refresh(record)
        return record

    async def revoke(
        self,
        session: AsyncSession,
        record: RefreshToken,
    ) -> RefreshToken:
        """Revoke a refresh token immediately."""
        record.is_revoked = True
        session.add(record)
        await session.commit()
        await session.refresh(record)
        return record


default_refresh_token_dao = RefreshTokenDAO()
