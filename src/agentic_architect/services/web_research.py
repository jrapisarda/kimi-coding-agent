"""Web research integration using duckduckgo search."""

from __future__ import annotations

import datetime as dt
from typing import List

from duckduckgo_search import DDGS

from ..config import ResearchConfig
from ..database import PatternCache, session_scope


class WebResearchService:
    """Performs web searches with lightweight caching in SQLite."""

    def __init__(self, research_config: ResearchConfig, session_factory) -> None:  # type: ignore[no-untyped-def]
        self._config = research_config
        self._session_factory = session_factory

    def search(self, query: str) -> List[dict]:
        """Search the web with caching."""

        cache_key = f"research::{query}"
        with session_scope(self._session_factory) as session:
            cache = (
                session.query(PatternCache)
                .filter_by(pattern_key=cache_key)
                .first()
            )
            if cache:
                cached_at = cache.updated_at or cache.created_at
                if cached_at and cached_at > dt.datetime.utcnow() - dt.timedelta(hours=self._config.cache_ttl_hours):
                    return cache.extra.get("results", [])

        results = list(DDGS().text(query, max_results=self._config.max_results))
        with session_scope(self._session_factory) as session:
            entry = session.query(PatternCache).filter_by(pattern_key=cache_key).first()
            if entry:
                entry.content = query
                entry.extra = {"results": results}
            else:
                session.add(
                    PatternCache(
                        pattern_key=cache_key,
                        content=query,
                        extra={"results": results},
                    )
                )
        return results


__all__ = ["WebResearchService"]
