"""Mock moderation checks for generated content."""
from __future__ import annotations

import re

BLOCKED_PATTERNS = [re.compile(pattern, re.IGNORECASE) for pattern in [r"spam", r"malware"]]


def passes_moderation(text: str) -> bool:
    return not any(pattern.search(text) for pattern in BLOCKED_PATTERNS)
