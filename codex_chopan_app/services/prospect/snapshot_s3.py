"""Snapshot helpers that emulate S3 versioned storage."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List
from uuid import uuid4


@dataclass
class Snapshot:
    snapshot_id: str
    stored_at: datetime
    artifacts: List[dict[str, str]]


class SnapshotStore:
    def __init__(self) -> None:
        self._store: Dict[str, Snapshot] = {}

    def create(self, artifacts: List[dict[str, str]]) -> Snapshot:
        snapshot = Snapshot(snapshot_id=str(uuid4()), stored_at=datetime.utcnow(), artifacts=artifacts)
        self._store[snapshot.snapshot_id] = snapshot
        return snapshot

    def restore(self, snapshot_id: str) -> Snapshot:
        return self._store[snapshot_id]

    def list_ids(self) -> List[str]:
        return list(self._store)
