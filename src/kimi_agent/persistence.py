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


@dataclass
class StepRecord:
    run_id: str
    step: str
    sequence: int
    input_payload: Dict[str, Any]
    output_payload: Dict[str, Any]
    created_at: datetime


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
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS step_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    step TEXT NOT NULL,
                    sequence INTEGER NOT NULL,
                    handoff_json TEXT,
                    output_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
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

    def add_step(
        self,
        run_id: str,
        step: str,
        sequence: int,
        handoff: Optional[Dict[str, Any]],
        output: Dict[str, Any],
    ) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO step_logs (run_id, step, sequence, handoff_json, output_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    step,
                    sequence,
                    json.dumps(handoff) if handoff is not None else None,
                    json.dumps(output),
                ),
            )

    def list_steps(self, run_id: str) -> Iterable[StepRecord]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT step, sequence, handoff_json, output_json, created_at
                FROM step_logs
                WHERE run_id = ?
                ORDER BY sequence
                """,
                (run_id,),
            )
            for step, sequence, handoff_json, output_json, created_at in cursor.fetchall():
                yield StepRecord(
                    run_id=run_id,
                    step=step,
                    sequence=sequence,
                    input_payload=json.loads(handoff_json) if handoff_json else {},
                    output_payload=json.loads(output_json),
                    created_at=datetime.fromisoformat(created_at),
                )
