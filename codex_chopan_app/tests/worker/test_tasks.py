"""Worker task tests."""
from __future__ import annotations

from codex_chopan_app.services.worker import tasks


def test_generate_content_task() -> None:
    result = tasks.generate_content("example")
    assert result["draft"] == "EXAMPLE"


def test_prospect_score_task() -> None:
    result = tasks.prospect_score("Org", 0.5)
    assert result["score"] == "0.60"
