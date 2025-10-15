"""Pattern caching utilities for reusing frequently generated templates."""

from __future__ import annotations

from typing import Dict, Optional

from ..database import PatternCache, session_scope


class PatternCacheService:
    """Stores and retrieves reusable patterns in SQLite."""

    def __init__(self, session_factory) -> None:  # type: ignore[no-untyped-def]
        self._session_factory = session_factory

    def get(self, key: str) -> Optional[str]:
        with session_scope(self._session_factory) as session:
            entry = session.query(PatternCache).filter_by(pattern_key=key).first()
            if entry:
                return entry.content
        return None

    def set(self, key: str, content: str, metadata: Optional[Dict[str, str]] = None) -> None:
        with session_scope(self._session_factory) as session:
            entry = session.query(PatternCache).filter_by(pattern_key=key).first()
            if entry:
                entry.content = content
                entry.extra = metadata or {}
            else:
                session.add(PatternCache(pattern_key=key, content=content, extra=metadata or {}))


__all__ = ["PatternCacheService"]
