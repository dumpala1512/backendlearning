"""
Re-export Watchlist ORM model for compatibility.
"""
from app.models.watchlist import Watchlist, WatchlistORM

__all__ = ["Watchlist", "WatchlistORM"]
