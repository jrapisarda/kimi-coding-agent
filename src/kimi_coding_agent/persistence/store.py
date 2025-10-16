"""SQLite persistence utilities."""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterator, List

from ..schemas import AgentStepResult, RunConfig, RunResult, RunStatus


class RunStore:
    """Persists run metadata, step payloads, and artifacts."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with self._connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    config_payload TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS steps (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    agent_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    completed_at TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    FOREIGN KEY (run_id) REFERENCES runs(run_id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS artifacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    artifact_type TEXT NOT NULL,
                    path TEXT NOT NULL,
                    description TEXT,
                    FOREIGN KEY (run_id) REFERENCES runs(run_id)
                )
                """
            )
            conn.commit()

    def record_run_start(self, run_id: str, config: RunConfig, started_at: datetime) -> None:
        with self._connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO runs(run_id, status, started_at, config_payload) VALUES(?,?,?,?)",
                (run_id, RunStatus.RUNNING.value, started_at.isoformat(), json.dumps(config.model_dump(), default=str)),
            )
            conn.commit()

    def finalize_run(self, run_id: str, status: RunStatus, completed_at: datetime) -> None:
        with self._connection() as conn:
            conn.execute(
                "UPDATE runs SET status = ?, completed_at = ? WHERE run_id = ?",
                (status.value, completed_at.isoformat(), run_id),
            )
            conn.commit()

    def record_step(
        self,
        run_id: str,
        agent_name: str,
        status: RunStatus,
        started_at: datetime,
        completed_at: datetime,
        payload: Dict,
    ) -> None:
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO steps(run_id, agent_name, status, started_at, completed_at, payload)
                VALUES(?,?,?,?,?,?)
                """,
                (
                    run_id,
                    agent_name,
                    status.value,
                    started_at.isoformat(),
                    completed_at.isoformat(),
                    json.dumps(payload, default=str),
                ),
            )
            conn.commit()

    def record_artifact(self, run_id: str, artifact_type: str, path: Path, description: str) -> None:
        with self._connection() as conn:
            conn.execute(
                "INSERT INTO artifacts(run_id, artifact_type, path, description) VALUES(?,?,?,?)",
                (run_id, artifact_type, str(path), description),
            )
            conn.commit()

    def load_run(self, run_id: str) -> RunResult:
        with self._connection() as conn:
            run_row = conn.execute(
                "SELECT run_id, status, started_at, completed_at FROM runs WHERE run_id = ?",
                (run_id,),
            ).fetchone()
            if run_row is None:
                raise KeyError(f"Run {run_id} not found")
            step_rows = conn.execute(
                "SELECT agent_name, status, started_at, completed_at, payload FROM steps WHERE run_id = ? ORDER BY id",
                (run_id,),
            ).fetchall()
        steps: List[AgentStepResult] = []
        for row in step_rows:
            steps.append(
                AgentStepResult(
                    agent_name=row[0],
                    status=RunStatus(row[1]),
                    started_at=datetime.fromisoformat(row[2]),
                    completed_at=datetime.fromisoformat(row[3]),
                    payload=json.loads(row[4]),
                )
            )
        return RunResult(
            run_id=run_row[0],
            status=RunStatus(run_row[1]),
            started_at=datetime.fromisoformat(run_row[2]),
            completed_at=datetime.fromisoformat(run_row[3]) if run_row[3] else datetime.fromisoformat(run_row[2]),
            steps=steps,
            contexts={},
        )

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        try:
            yield conn
        finally:
            conn.close()
