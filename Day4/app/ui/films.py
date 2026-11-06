"""
Server-rendered UI router for film search using Jinja2 and HTMX.

Provides completely separate HTML-rendering endpoints:
- GET /ui/films: Full HTML5 film search landing page.
- GET /ui/films/search: HTMX fragment endpoint returning matching film cards.

Follows clean layered architecture:
Route (HTTP / query parsing) -> DAO (database queries) -> Database -> TemplateResponse
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.dao.film_dao import FilmDAO
from app.dependencies import get_db, get_film_dao

# Resolve the templates directory relative to this module: app/templates
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Dedicated UI router separate from /api
router = APIRouter(tags=["UI - Films"])


@router.get("/films", response_class=HTMLResponse, summary="Film Landing Page")
async def film_landing_page(request: Request) -> HTMLResponse:
    """
    Render the main server-rendered film landing page.

    The page contains the HTML5 document layout, HTMX CDN script,
    search input, and an initially empty results container displaying no films.
    This route always returns HTML and never returns JSON.
    """
    context: dict[str, Any] = {
        "request": request,
    }
    return templates.TemplateResponse(
        request=request,
        name="films.html",
        context=context,
    )


@router.get("/films/search", response_class=HTMLResponse)
async def search_films_ui(
    request: Request,
    q: str | None = Query(default=None, description="Search query string for film title"),
    limit: int = Query(default=10, ge=1, le=100, description="Page limit for films"),
    db: AsyncSession = Depends(get_db),
    dao: FilmDAO = Depends(get_film_dao),
) -> HTMLResponse:
    """
    HTMX fragment endpoint returning server-rendered HTML cards for matching films.

    Accepts `?q=<search term>` query parameter. If search term is empty or None,
    all films are listed up to limit. Delegates query execution entirely to the FilmDAO layer.
    Never accesses SQLAlchemy queries directly and never returns JSON.
    """
    search_term = q.strip() if q else ""
    films = await dao.search_films(session=db, search_term=search_term, limit=limit)

    context: dict[str, Any] = {
        "request": request,
        "films": films,
        "query": search_term,
    }
    return templates.TemplateResponse(
        request=request,
        name="film_results.html",
        context=context,
    )
