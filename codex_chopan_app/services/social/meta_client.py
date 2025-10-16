"""Stub Meta (Facebook/Instagram) client."""
from __future__ import annotations

from typing import Dict


class MetaClient:
    def publish(self, message: str) -> Dict[str, str]:
        return {"id": "meta-001", "status": "published", "message": message}
