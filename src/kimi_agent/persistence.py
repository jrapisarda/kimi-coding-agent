"""SQLite persistence for run artifacts."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

DEFAULT_DB = Path.home() / ".kimi_agent" / "runs.db"


@dataclass
class RunRecord:
    run_id: str
    status: str
    started_at: datetime
    finished_at: Optional[datetime]
    summary: str
    metadata: Dict[str, Any]


class RunStore:
    """Simple SQLite wrapper for persisting run information."""

    def __init__(self, db_path: Path = DEFAULT_DB) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    summary TEXT,
                    metadata_json TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS artifacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    label TEXT,
                    body_json TEXT NOT NULL,
                    FOREIGN KEY(run_id) REFERENCES runs(run_id)
                )
                """
            )

    def upsert_run(self, record: RunRecord) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO runs (run_id, status, started_at, finished_at, summary, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(run_id) DO UPDATE SET
                    status=excluded.status,
                    finished_at=excluded.finished_at,
                    summary=excluded.summary,
                    metadata_json=excluded.metadata_json
                """,
                (
                    record.run_id,
                    record.status,
                    record.started_at.isoformat(),
                    record.finished_at.isoformat() if record.finished_at else None,
                    record.summary,
                    json.dumps(record.metadata),
                ),
            )

    def add_artifact(self, run_id: str, kind: str, body: Dict[str, Any], label: Optional[str] = None) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO artifacts (run_id, kind, label, body_json) VALUES (?, ?, ?, ?)",
                (run_id, kind, label, json.dumps(body)),
            )

    def list_artifacts(self, run_id: str) -> Iterable[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT kind, label, body_json FROM artifacts WHERE run_id = ? ORDER BY id",
                (run_id,),
            )
            for kind, label, body_json in cursor.fetchall():
                yield {"kind": kind, "label": label, "body": json.loads(body_json)}
