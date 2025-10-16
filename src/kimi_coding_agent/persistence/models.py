"""Data models persisted to SQLite."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict

from ..schemas import RunStatus


@dataclass
class RunRecord:
    run_id: str
    status: RunStatus
    started_at: datetime
    completed_at: datetime | None
    config_payload: Dict[str, Any]


@dataclass
class StepRecord:
    run_id: str
    agent_name: str
    status: RunStatus
    started_at: datetime
    completed_at: datetime
    payload: Dict[str, Any]


@dataclass
class ArtifactRecord:
    run_id: str
    artifact_type: str
    path: str
    description: str
