"""Robots.txt compliance helpers."""
from __future__ import annotations

from urllib.parse import urlparse

ALLOWED_DOMAINS = {"chopan.example.org", "arts.example.org", "story.ai"}


def is_allowed(url: str) -> bool:
    domain = urlparse(url).netloc
    return domain in ALLOWED_DOMAINS
