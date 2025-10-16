"""Prospect service unit tests."""
from __future__ import annotations

import pytest

from codex_chopan_app.services.prospect.main import ProspectService, _service


def test_discover_returns_scored_prospects() -> None:
    service: ProspectService = _service
    prospects = service.discover("Chopan impact", 2)
    assert len(prospects) == 2
    assert all(prospect.score > 0 for prospect in prospects)


def test_discover_rejects_disallowed_domain(monkeypatch: pytest.MonkeyPatch) -> None:
    service: ProspectService = _service

    def fake_search(query: str, limit: int):
        return [{"organization": "Bad", "website": "https://blocked.example.com"}]

    monkeypatch.setattr(service.search_client, "search", fake_search)
    with pytest.raises(Exception):
        service.discover("Bad actor", 1)
