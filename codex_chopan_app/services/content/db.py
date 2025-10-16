"""In-memory persistence for content artifacts."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict


@dataclass
class ContentDraft:
    draft_id: str
    brief: str
    language: str
    content: str
    created_at: datetime
    scheduled_time: datetime | None
    moderation_passed: bool


class ContentRepository:
    def __init__(self) -> None:
        self._drafts: Dict[str, ContentDraft] = {}

    def save(self, draft: ContentDraft) -> ContentDraft:
        self._drafts[draft.draft_id] = draft
        return draft

    def get(self, draft_id: str) -> ContentDraft:
        return self._drafts[draft_id]

    def list_all(self) -> list[ContentDraft]:
        return list(self._drafts.values())
