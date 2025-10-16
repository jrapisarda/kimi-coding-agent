"""FastAPI application exposing the content microservice."""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import Depends, FastAPI
from pydantic import BaseModel

from .db import ContentDraft, ContentRepository
from .moderation import passes_moderation
from .openai_client import OpenAIClient


class ContentRequest(BaseModel):
    brief: str
    language: str = "en"
    tone: Optional[str] = None
    scheduled_time: Optional[datetime] = None


class ContentResponse(BaseModel):
    draft_id: str
    content: str
    language: str
    moderation_passed: bool
    scheduled_time: Optional[datetime]


class ContentService:
    def __init__(self, repo: ContentRepository, client: OpenAIClient) -> None:
        self.repo = repo
        self.client = client

    def create_draft(self, request: ContentRequest) -> ContentDraft:
        content = self.client.generate(request.brief, request.language, request.tone)
        moderation_passed = passes_moderation(content)
        scheduled = request.scheduled_time or datetime.utcnow() + timedelta(hours=1)
        draft = ContentDraft(
            draft_id=str(uuid4()),
            brief=request.brief,
            language=request.language,
            content=content,
            created_at=datetime.utcnow(),
            scheduled_time=scheduled,
            moderation_passed=moderation_passed,
        )
        self.repo.save(draft)
        return draft

    def translate(self, content: str, target_language: str) -> str:
        return self.client.translate(content, target_language)


_templates_dir = Path(__file__).parent / "templates"
_repo = ContentRepository()
_client = OpenAIClient(_templates_dir)
_service = ContentService(_repo, _client)

app = FastAPI(title="Content Service", version="1.0.0")


def get_service() -> ContentService:
    return _service


@app.post("/draft", response_model=ContentResponse)
async def create_draft(request: ContentRequest, service: ContentService = Depends(get_service)) -> ContentResponse:
    draft = service.create_draft(request)
    moderation_passed = getattr(draft, "moderation_passed", True)
    return ContentResponse(
        draft_id=draft.draft_id,
        content=draft.content,
        language=draft.language,
        moderation_passed=moderation_passed,
        scheduled_time=draft.scheduled_time,
    )


@app.post("/translate")
async def translate(text: str, target_language: str, service: ContentService = Depends(get_service)) -> dict[str, str]:
    return {"translated": service.translate(text, target_language)}
