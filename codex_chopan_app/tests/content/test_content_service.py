"""Unit tests for the content service."""
from __future__ import annotations

from codex_chopan_app.services.content.main import ContentRequest, get_service


def test_generate_and_translate() -> None:
    service = get_service()
    request = ContentRequest(brief="Tell a story", language="en", tone="warm")
    draft = service.create_draft(request)
    assert draft.language == "en"
    translated = service.translate(draft.content, "ur")
    assert translated.startswith("[ur]")
