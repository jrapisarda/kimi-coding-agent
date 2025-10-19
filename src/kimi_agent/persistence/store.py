from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


class SQLiteRunStore:
    """
    Minimal SQLite-backed persistence layer for sprint one.

    The schema follows a simple runs/steps/artifacts model; richer artefact
    handling will be layered on in subsequent sprints.
    """

    def __init__(self, db_path: Path) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

    def initialize(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL UNIQUE,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    status TEXT,
                    target_path TEXT,
                    prompt TEXT,
                    input_docs TEXT,
                    config_json TEXT,
                    packaging_path TEXT,
                    error TEXT
                );

                CREATE TABLE IF NOT EXISTS steps (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    agent_name TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    status TEXT,
                    input_payload TEXT,
                    output_payload TEXT,
                    error TEXT
                );

                CREATE TABLE IF NOT EXISTS artifacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    step_name TEXT NOT NULL,
                    artifact_type TEXT,
                    path TEXT,
                    payload_json TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS run_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    message TEXT,
                    payload_json TEXT,
                    created_at TEXT NOT NULL
                );
                """
            )

    def record_run_start(
        self,
        run_id: str,
        target_path: str,
        prompt: Optional[str],
        input_docs: Optional[str],
        config: Dict[str, Any],
    ) -> None:
        self.initialize()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO runs (run_id, started_at, status, target_path, prompt, input_docs, config_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    self._timestamp(),
                    "running",
                    target_path,
                    prompt,
                    input_docs,
                    json.dumps(config),
                ),
            )

    def record_run_complete(
        self,
        run_id: str,
        status: str,
        completed_at: datetime,
        packaging_path: Optional[Path],
        error: Optional[str] = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE runs
                SET completed_at = ?, status = ?, packaging_path = ?, error = ?
                WHERE run_id = ?
                """,
                (
                    completed_at.isoformat(),
                    status,
                    str(packaging_path) if packaging_path else None,
                    error,
                    run_id,
                ),
            )

    def record_step_start(
        self,
        run_id: str,
        agent_name: str,
        input_payload: Dict[str, Any],
    ) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO steps (run_id, agent_name, started_at, status, input_payload)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    agent_name,
                    self._timestamp(),
                    "running",
                    json.dumps(input_payload),
                ),
            )
            return int(cursor.lastrowid)

    def record_step_complete(
        self,
        step_id: int,
        output_payload: Dict[str, Any],
        status: str,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE steps
                SET completed_at = ?, status = ?, output_payload = ?
                WHERE id = ?
                """,
                (
                    self._timestamp(),
                    status,
                    json.dumps(output_payload),
                    step_id,
                ),
            )

    def record_step_failed(self, step_id: int, error: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE steps
                SET completed_at = ?, status = ?, error = ?
                WHERE id = ?
                """,
                (
                    self._timestamp(),
                    "failed",
                    error,
                    step_id,
                ),
            )

    def record_artifact(
        self,
        run_id: str,
        step_name: str,
        artifact_type: str,
        path: Optional[Path],
        payload: Dict[str, Any],
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO artifacts (run_id, step_name, artifact_type, path, payload_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    step_name,
                    artifact_type,
                    str(path) if path else None,
                    json.dumps(payload),
                    self._timestamp(),
                ),
            )

    def record_event(
        self,
        run_id: str,
        event_type: str,
        message: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO run_events (run_id, event_type, message, payload_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    event_type,
                    message,
                    json.dumps(payload or {}),
                    self._timestamp(),
                ),
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._db_path)
        return connection

    @staticmethod
    def _timestamp() -> str:
        return datetime.utcnow().isoformat()
