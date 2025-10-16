"""Orchestration pipeline for the multi-agent system."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Sequence

from ..config import Settings
from ..packaging.archiver import RunPackager
from ..persistence.store import RunStore
from ..sandbox.snapshot import SnapshotManager
from ..schemas import AgentStepResult, RunConfig, RunResult, RunStatus
from ..agents.base import BaseAgent

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """Coordinates Requirements → Coding → Testing → Documentation agents."""

    def __init__(
        self,
        *,
        store: RunStore,
        snapshot_manager: SnapshotManager,
        packager: RunPackager,
        agents: Sequence[BaseAgent],
    ) -> None:
        self.store = store
        self.snapshot_manager = snapshot_manager
        self.packager = packager
        self.agents = list(agents)

    @classmethod
    def from_settings(cls, settings: Settings, agents: Sequence[BaseAgent]) -> "AgentOrchestrator":
        database_path = settings.resolve_database_path()
        store = RunStore(database_path)
        snapshot_dir = settings.state_dir / "snapshots"
        packager = RunPackager(settings.state_dir / "dist")
        snapshot_manager = SnapshotManager(snapshot_dir)
        return cls(store=store, snapshot_manager=snapshot_manager, packager=packager, agents=agents)

    def execute(self, config: RunConfig) -> RunResult:
        run_id = uuid.uuid4().hex
        started_at = datetime.now(timezone.utc)
        self.store.record_run_start(run_id, config, started_at)
        config.target_path.mkdir(parents=True, exist_ok=True)
        snapshot_path = self.snapshot_manager.create_snapshot(run_id, config.target_path)
        shared_state: Dict[str, Dict] = {}
        steps: List[AgentStepResult] = []
        status = RunStatus.SUCCEEDED
        failure: Exception | None = None

        for agent in self.agents:
            step_start = datetime.now(timezone.utc)
            payload: Dict
            step_status = RunStatus.SUCCEEDED
            try:
                payload = agent.run(config=config, shared_state=shared_state)
            except Exception as exc:  # pragma: no cover - defensive guard
                logger.exception("Agent %s failed", agent.name)
                payload = {"error": str(exc)}
                step_status = RunStatus.FAILED
                failure = exc
            step_end = datetime.now(timezone.utc)
            self.store.record_step(run_id, agent.name, step_status, step_start, step_end, payload)
            steps.append(
                AgentStepResult(
                    agent_name=agent.name,
                    status=step_status,
                    started_at=step_start,
                    completed_at=step_end,
                    payload=payload,
                )
            )
            if step_status is RunStatus.FAILED:
                status = RunStatus.FAILED
                break

        if status is RunStatus.FAILED:
            self.snapshot_manager.restore_snapshot(snapshot_path, config.target_path)
        else:
            archive_path = self.packager.package(run_id, config.target_path, shared_state)
            self.store.record_artifact(run_id, "dist", archive_path, "Packaged run output")
            self.snapshot_manager.cleanup_snapshot(snapshot_path)

        completed_at = datetime.now(timezone.utc)
        self.store.finalize_run(run_id, status, completed_at)
        result = RunResult(
            run_id=run_id,
            status=status,
            started_at=started_at,
            completed_at=completed_at,
            steps=steps,
            contexts=shared_state,
        )
        if failure:
            return result
        return result
