"""Stub LinkedIn API client."""
from __future__ import annotations

from typing import Dict


class LinkedInClient:
    def publish(self, message: str) -> Dict[str, str]:
        return {"id": "linkedin-001", "status": "published", "message": message}
