"""In-memory store for prospect discoveries."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List


@dataclass
class Prospect:
    organization: str
    website: str
    score: float
    provenance_key: str
    discovered_at: datetime


class ProspectRepository:
    def __init__(self) -> None:
        self._prospects: Dict[str, Prospect] = {}

    def save(self, prospect: Prospect) -> Prospect:
        self._prospects[prospect.organization] = prospect
        return prospect

    def list_all(self) -> List[Prospect]:
        return list(self._prospects.values())
