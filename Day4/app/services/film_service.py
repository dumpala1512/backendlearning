from __future__ import annotations

from collections.abc import AsyncGenerator
import contextlib
from datetime import datetime, timezone
import logging
from typing import Any, Sequence
import uuid

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import async_session_factory
from app.dao.film_dao import FilmDAO
from app.dao.review_dao import ReviewDAO
from app.exceptions.film import FilmHasActiveReviewsError, FilmNotFoundError
from app.models.film import Film, FilmORM
import math
from app.schemas.film import (
    CursorFilmResponse,
    FilmFilterQuery,
    FilmResponse,
    PaginatedFilmResponse,
)
from app.services.redis_service import RedisService

logger = logging.getLogger("film_service")


def get_film_dao() -> FilmDAO:
    """Dependency provider returning a FilmDAO instance."""
    return FilmDAO()


def get_review_dao() -> ReviewDAO:
    """Dependency provider returning a ReviewDAO instance."""
    return ReviewDAO()


class FilmService:
    """
    Service layer for Film business logic and orchestration.
    Receives FilmDAO, ReviewDAO, and RedisService via constructor injection.
    Implements deterministic read-through caching and pattern-based cache invalidation.
    """

    def __init__(
        self,
        dao: FilmDAO = Depends(get_film_dao),
        review_dao: ReviewDAO | None = None,
        redis_service: RedisService | None = None,
    ):
        self.dao = dao
        self.review_dao = review_dao or ReviewDAO()
        self.redis_service = redis_service

    @staticmethod
    def build_film_list_cache_key(
        genre: str | None = None,
        year_from: int | None = None,
        year_to: int | None = None,
        director: str | None = None,
        page: int = 1,
        page_size: int = 10,
        limit: int | None = 10,
    ) -> str:
        """
        Build deterministic, canonical cache keys matching query filters.
        e.g., 'films:list', 'films:list:genre=action', 'films:list:genre=action:limit=20'
        """
        params: list[str] = []
        if genre is not None and genre.strip():
            params.append(f"genre={genre.strip().lower()}")
        if year_from is not None:
            params.append(f"start_year={year_from}")
        if year_to is not None:
            params.append(f"end_year={year_to}")
        if director is not None and director.strip():
            params.append(f"director={director.strip().lower()}")
        if page != 1:
            params.append(f"page={page}")
        if page_size != 10:
            params.append(f"page_size={page_size}")
        if limit is not None and limit != 10:
            params.append(f"limit={limit}")

        if not params:
            return "films:list"
        return f"films:list:{':'.join(sorted(params))}"

    @staticmethod
    def _serialize_film(film: Any) -> dict[str, Any]:
        """Convert a film ORM/model instance into a JSON-serializable dictionary."""
        if isinstance(film, dict):
            return film
        created_at_val = getattr(film, "created_at", None)
        if hasattr(created_at_val, "isoformat"):
            created_at_str = created_at_val.isoformat()
        else:
            created_at_str = str(created_at_val) if created_at_val else None

        return {
            "id": str(getattr(film, "id", "")),
            "title": getattr(film, "title", ""),
            "director": getattr(film, "director", ""),
            "release_year": getattr(film, "release_year", 0),
            "genre": getattr(film, "genre", ""),
            "description": getattr(film, "description", ""),
            "is_active": getattr(film, "is_active", True),
            "created_at": created_at_str,
        }

    @staticmethod
    def _deserialize_cached_film(data: dict[str, Any]) -> FilmResponse:
        """Reconstruct a FilmResponse instance from cached dictionary, converting types for strict mode."""
        res = dict(data)
        if "created_at" in res and isinstance(res["created_at"], str):
            try:
                res["created_at"] = datetime.fromisoformat(res["created_at"])
            except Exception:
                res["created_at"] = datetime.now(timezone.utc)
        if "id" in res and isinstance(res["id"], str):
            try:
                res["id"] = uuid.UUID(res["id"])
            except Exception:
                pass
        return FilmResponse.model_validate(res)

    @staticmethod
    def build_film_cache_key(film_id: uuid.UUID | str) -> str:
        """Build deterministic cache key for a single film."""
        return f"film:{film_id}"

    async def get_by_id(self, session: AsyncSession, film_id: uuid.UUID) -> Any:
        """
        Retrieve a film by UUID with read-through Redis caching or raise domain FilmNotFoundError.
        """
        cache_key = self.build_film_cache_key(film_id)
        if self.redis_service:
            cached_data = await self.redis_service.get(cache_key)
            if cached_data is not None:
                logger.info("Cache hit for %s", cache_key)
                if isinstance(cached_data, dict):
                    return self._deserialize_cached_film(cached_data)
                return cached_data

        logger.info("Cache miss for %s", cache_key)
        film = await self.dao.get_by_id(session, film_id)
        if film is None:
            raise FilmNotFoundError(film_id=film_id)

        if self.redis_service:
            serialized_film = self._serialize_film(film)
            await self.redis_service.set(
                cache_key,
                serialized_film,
                ttl=settings.CACHE_TTL_SECONDS,
            )

        return film

    async def get_film(self, session: AsyncSession, film_id: uuid.UUID) -> Any:
        """Alias for get_by_id."""
        return await self.get_by_id(session=session, film_id=film_id)

    async def get_film_details(self, session: AsyncSession, film_id: uuid.UUID) -> Any:
        """Alias for get_by_id with explicit naming for single film retrieval."""
        return await self.get_by_id(session=session, film_id=film_id)

    async def list_films_paginated(
        self,
        session: AsyncSession,
        genre: str | None = None,
        year_from: int | None = None,
        year_to: int | None = None,
        director: str | None = None,
        page: int = 1,
        limit: int = 10,
        page_size: int | None = None,
        filters: FilmFilterQuery | None = None,
    ) -> PaginatedFilmResponse:
        """
        Retrieve films with offset-based pagination and dynamic filtering.
        Calculates total records and total pages efficiently in SQL.
        Standardized on `limit` with `page_size` alias.
        """
        effective_limit = page_size if page_size is not None else limit
        if filters is not None:
            genre = filters.genre if genre is None else genre
            year_from = filters.year_from if year_from is None else year_from
            year_to = filters.year_to if year_to is None else year_to
            director = filters.director if director is None else director
            page = filters.page
            effective_limit = filters.limit if filters.limit is not None else (filters.page_size or effective_limit)

        cache_key = self.build_film_list_cache_key(
            genre=genre,
            year_from=year_from,
            year_to=year_to,
            director=director,
            page=page,
            page_size=effective_limit,
            limit=effective_limit,
        )

        if self.redis_service:
            cached_data = await self.redis_service.get(cache_key)
            if cached_data is not None and isinstance(cached_data, dict):
                logger.info("Cache hit for %s", cache_key)
                items = [self._deserialize_cached_film(item) for item in cached_data.get("items", [])]
                return PaginatedFilmResponse(
                    page=cached_data.get("page", page),
                    limit=cached_data.get("limit", cached_data.get("page_size", effective_limit)),
                    total=cached_data.get("total", len(items)),
                    total_pages=cached_data.get("total_pages", 1),
                    total_records=cached_data.get("total", len(items)),
                    items=items,
                )

        logger.info("Cache miss for %s", cache_key)
        films, total = await self.dao.list_films_paginated(
            session=session,
            genre=genre,
            year_from=year_from,
            year_to=year_to,
            director=director,
            page=page,
            limit=effective_limit,
        )
        total_pages = math.ceil(total / effective_limit) if total > 0 else 0
        validated_films = [FilmResponse.model_validate(f) for f in films]

        response = PaginatedFilmResponse(
            page=page,
            limit=effective_limit,
            total=total,
            total_pages=total_pages,
            total_records=total,
            items=validated_films,
        )

        if self.redis_service:
            cache_payload = {
                "page": page,
                "limit": effective_limit,
                "page_size": effective_limit,
                "total": total,
                "total_pages": total_pages,
                "items": [self._serialize_film(f) for f in films],
            }
            await self.redis_service.set(
                cache_key,
                cache_payload,
                ttl=settings.CACHE_TTL_SECONDS,
            )

        return response

    async def list_films_cursor(
        self,
        session: AsyncSession,
        cursor: str | None = None,
        limit: int = 10,
        genre: str | None = None,
        year_from: int | None = None,
        year_to: int | None = None,
        director: str | None = None,
        filters: FilmFilterQuery | None = None,
    ) -> CursorFilmResponse:
        """
        Retrieve films with cursor-based pagination and dynamic filtering.
        Returns opaque next_cursor or None when no more records exist.
        """
        if filters is not None:
            cursor = filters.cursor if cursor is None else cursor
            limit = filters.limit if filters.limit is not None else (filters.page_size if limit == 10 else limit)
            genre = filters.genre if genre is None else genre
            year_from = filters.year_from if year_from is None else year_from
            year_to = filters.year_to if year_to is None else year_to
            director = filters.director if director is None else director

        films, next_cursor = await self.dao.list_films_cursor(
            session=session,
            cursor=cursor,
            limit=limit,
            genre=genre,
            year_from=year_from,
            year_to=year_to,
            director=director,
        )
        validated_films = [FilmResponse.model_validate(f) for f in films]
        return CursorFilmResponse(
            items=validated_films,
            next_cursor=next_cursor,
            limit=limit,
        )

    async def list_films(
        self,
        session: AsyncSession,
        genre: str | None = None,
        year_from: int | None = None,
        year_to: int | None = None,
        start_year: int | None = None,
        end_year: int | None = None,
        director: str | None = None,
        limit: int = 10,
    ) -> list[Any]:
        """
        Retrieve films with read-through caching.
        Checks Redis first; on cache hit skips database query entirely.
        On cache miss queries database, stores serialized response in Redis with configurable TTL, and returns results.
        """
        effective_from = year_from if year_from is not None else start_year
        effective_to = year_to if year_to is not None else end_year

        cache_key = self.build_film_list_cache_key(
            genre=genre,
            year_from=effective_from,
            year_to=effective_to,
            director=director,
            limit=limit,
        )

        if self.redis_service:
            cached_data = await self.redis_service.get(cache_key)
            if cached_data is not None:
                if isinstance(cached_data, dict) and "items" in cached_data:
                    logger.info("Cache hit for %s", cache_key)
                    return [self._deserialize_cached_film(item) for item in cached_data["items"]]
                elif isinstance(cached_data, list):
                    logger.info("Cache hit for %s", cache_key)
                    return [self._deserialize_cached_film(item) for item in cached_data]

        logger.info("Cache miss for %s", cache_key)
        films = await self.dao.list_films(
            session=session,
            genre=genre,
            year_from=effective_from,
            year_to=effective_to,
            director=director,
            limit=limit,
        )

        if self.redis_service:
            serialized_films = [self._serialize_film(f) for f in films]
            await self.redis_service.set(
                cache_key,
                serialized_films,
                ttl=settings.CACHE_TTL_SECONDS,
            )

        return films

    async def _invalidate_film_list_cache(self, film_id: uuid.UUID | None = None) -> None:
        """Centralized helper to safely invalidate film list caches and individual film cache in Redis."""
        if self.redis_service:
            try:
                await self.redis_service.delete_by_pattern("films:list*")
                if film_id is not None:
                    await self.redis_service.delete(self.build_film_cache_key(film_id))
                logger.info("Invalidated film cache")
            except Exception as exc:
                logger.warning("Failed to invalidate film cache: %s", exc)

    async def create_film(
        self,
        session: AsyncSession,
        title: str,
        director: str,
        release_year: int,
        genre: str,
        description: str = "",
    ) -> Film:
        """
        Validate and create a new film with UUID PK.
        Invalidates all cached film lists matching films:list*.
        """
        film = await self.dao.create(
            session=session,
            title=title.strip(),
            director=director.strip(),
            release_year=release_year,
            genre=genre.strip(),
            description=description.strip(),
            )
        logger.info(
            "Film '%s' created successfully with id %s",
            film.title,
            film.id,
            extra={"film_id": str(film.id), "title": film.title},
        )
        await self._invalidate_film_list_cache()
        return film

    async def update_film(
        self,
        session: AsyncSession,
        film_id: uuid.UUID,
        **updates,
    ) -> Film:
        """
        Update film attributes or raise domain FilmNotFoundError if missing.
        Invalidates all cached film lists matching films:list* and individual film cache.
        """
        film = await self.dao.update(session, film_id, **updates)
        if film is None:
            raise FilmNotFoundError(film_id=film_id)
        logger.info(
            "Film %s updated successfully",
            film_id,
            extra={"film_id": str(film_id)},
        )
        await self._invalidate_film_list_cache(film_id=film_id)
        return film

    async def delete_film(
        self,
        session: AsyncSession,
        film_id: uuid.UUID,
    ) -> bool:
        """
        Soft delete a film after verifying business rules:
        Rule 3: A film may not be soft deleted while it still has active reviews.
        Invalidates all cached film lists matching films:list* and individual film cache.
        """
        film = await self.dao.get_by_id(session, film_id)
        if film is None:
            raise FilmNotFoundError(film_id=film_id)

        # Check for active reviews associated with this film
        active_reviews = await self.review_dao.list_reviews(session, film_id=film_id)
        if len(active_reviews) > 0:
            logger.warning(
                "Film deletion blocked: film %s has %d active review(s)",
                film_id,
                len(active_reviews),
                extra={"film_id": str(film_id), "active_reviews_count": len(active_reviews)},
            )
            raise FilmHasActiveReviewsError(film_id=film_id, active_reviews_count=len(active_reviews))

        success = await self.dao.soft_delete(session, film_id)
        if not success:
            raise FilmNotFoundError(film_id=film_id)

        logger.info(
            "Film %s soft deleted successfully",
            film_id,
            extra={"film_id": str(film_id)},
        )
        await self._invalidate_film_list_cache(film_id=film_id)
        return True

    async def recalculate_film_stats(
        self,
        session: AsyncSession,
        film_id: uuid.UUID,
    ) -> Film | None:
        """
        Recalculate the film's total review count and average rating,
        and update the Film record.
        """
        film = await self.dao.get_by_id(session, film_id)
        if film is None:
            return None

        total_reviews = await self.review_dao.count_by_film_id(session, film_id)
        avg = await self.review_dao.average_rating(session, film_id)
        avg_rating = round(float(avg), 2) if avg is not None else None

        updated_film = await self.dao.update(
            session=session,
            film_id=film_id,
            total_reviews=total_reviews,
            average_rating=avg_rating,
        )
        await self._invalidate_film_list_cache(film_id=film_id)
        logger.info(
            "Film statistics recalculated: film_id=%s, total_reviews=%d, average_rating=%s",
            film_id,
            total_reviews,
            avg_rating,
            extra={"film_id": str(film_id), "total_reviews": total_reviews, "average_rating": avg_rating},
        )
        return updated_film


@contextlib.asynccontextmanager
async def get_background_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Provide an AsyncSession for background tasks running after response has been sent.
    Honors test dependency overrides on `get_db` when running under test harnesses.
    """
    from app.dependencies import get_db
    from app.main import app

    if get_db in app.dependency_overrides:
        override = app.dependency_overrides[get_db]
        gen = override()
        session = await anext(gen)
        try:
            yield session
        finally:
            try:
                await anext(gen)
            except (StopAsyncIteration, GeneratorExit):
                pass
    else:
        async with async_session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise


async def recalculate_film_stats_task(
    film_id: uuid.UUID,
    session: AsyncSession | None = None,
) -> Film | None:
    """
    Background task to recalculate total reviews and average rating for a film.
    Acquires an async database session via get_background_session() or uses provided session and updates the Film record.
    """
    logger.info("Background task started: recalculating stats for film_id=%s", film_id)
    if session is not None:
        service = FilmService(dao=FilmDAO(), review_dao=ReviewDAO())
        updated = await service.recalculate_film_stats(session=session, film_id=film_id)
        logger.info("Background task finished: stats updated for film_id=%s", film_id)
        return updated

    async with get_background_session() as bg_session:
        service = FilmService(dao=FilmDAO(), review_dao=ReviewDAO())
        updated = await service.recalculate_film_stats(session=bg_session, film_id=film_id)
    logger.info("Background task finished: stats updated for film_id=%s", film_id)
    return updated


# Default instance and module-level helpers for backward compatibility
_default_film_service = FilmService(dao=FilmDAO(), review_dao=ReviewDAO())


async def list_films(
    db: AsyncSession,
    genre: str | None = None,
    start_year: int | None = None,
    end_year: int | None = None,
    limit: int = 10,
) -> Sequence[FilmORM]:
    return await _default_film_service.list_films(
        session=db,
        genre=genre,
        start_year=start_year,
        end_year=end_year,
        limit=limit,
    )


async def get_film(db: AsyncSession, film_id: uuid.UUID) -> FilmORM:
    return await _default_film_service.get_by_id(session=db, film_id=film_id)


async def create_film(
    db: AsyncSession,
    title: str,
    director: str,
    release_year: int,
    genre: str,
    description: str = "",
) -> FilmORM:
    return await _default_film_service.create_film(
        session=db,
        title=title,
        director=director,
        release_year=release_year,
        genre=genre,
        description=description,
    )


async def update_film(db: AsyncSession, film_id: uuid.UUID, **updates) -> FilmORM:
    return await _default_film_service.update_film(session=db, film_id=film_id, **updates)


async def delete_film(db: AsyncSession, film_id: uuid.UUID) -> bool:
    return await _default_film_service.delete_film(session=db, film_id=film_id)
