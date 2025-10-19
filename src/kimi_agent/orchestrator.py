from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .config import AppConfig
from .persistence.store import SQLiteRunStore
from .packaging import ArtifactPackager, PackagingResult
from .sandbox import CommandRunner
from .sdk.openai_client import OpenAIClient
from .workspace import WorkspaceManager


LOGGER = logging.getLogger("kimi_agent.orchestrator")


@dataclass
class PipelineRequest:
    """Inputs supplied via the CLI for a given pipeline invocation."""

    run_id: str
    target_path: Path
    prompt: Optional[str]
    input_docs: Optional[Path]
    dry_run: bool


@dataclass
class AgentContext:
    """Mutable state shared across agent executions."""

    request: PipelineRequest
    config: AppConfig
    openai: OpenAIClient
    store: SQLiteRunStore
    command_runner: CommandRunner
    run_dir: Path
    run_metadata: Dict[str, str] = field(default_factory=dict)
    outputs: Dict[str, "AgentResult"] = field(default_factory=dict)


@dataclass
class AgentResult:
    """Structured payload returned by each agent execution."""

    name: str
    status: str
    summary: str
    details: Dict[str, Any] = field(default_factory=dict)
    artifacts: Dict[str, Dict[str, Any]] = field(default_factory=dict)


@dataclass
class RunResult:
    """Outcome of the full pipeline execution."""

    run_id: str
    status: str
    started_at: datetime
    completed_at: datetime
    packaging: Optional[PackagingResult]
    agent_results: List[AgentResult]


class Agent:
    """Base protocol for pipeline agents."""

    name: str

    def execute(self, context: AgentContext) -> AgentResult:  # pragma: no cover - documentation method
        raise NotImplementedError


class RunController:
    """Coordinate agent execution, persistence, and packaging."""

    def __init__(
        self,
        config: AppConfig,
        store: SQLiteRunStore,
        agents: Iterable[Agent],
        packager: ArtifactPackager,
        workspace_manager: Optional[WorkspaceManager] = None,
    ) -> None:
        self._config = config
        self._store = store
        self._agents = list(agents)
        self._packager = packager
        self._workspace = workspace_manager
        self._logger = LOGGER

    def execute(self, request: PipelineRequest, openai_client: OpenAIClient) -> RunResult:
        """Run the full Requirements -> Coding -> Testing -> Documentation pipeline."""
        started_at = datetime.utcnow()
        self._logger.info("Starting run %s", request.run_id)

        snapshot_path: Optional[Path] = None
        if self._workspace and not request.dry_run:
            snapshot_path = self._workspace.create_snapshot(request.run_id, request.target_path)

        run_dir = self._config.paths.data_dir / 'runs' / request.run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        command_runner = CommandRunner(
            run_dir=run_dir,
            dry_run=request.dry_run or self._config.dry_run,
            policy=self._config.sandbox,
        )

        self._store.record_run_start(
            run_id=request.run_id,
            target_path=str(request.target_path),
            prompt=request.prompt,
            input_docs=str(request.input_docs) if request.input_docs else None,
            config=self._config.to_dict(),
        )
        self._store.record_event(
            run_id=request.run_id,
            event_type="run_started",
            message="Run initialised and snapshot captured." if snapshot_path else "Run initialised.",
            payload={
                "target_path": str(request.target_path),
                "dry_run": request.dry_run,
                "snapshot": str(snapshot_path) if snapshot_path else None,
            },
        )

        context = AgentContext(
            request=request,
            config=self._config,
            openai=openai_client,
            store=self._store,
            command_runner=command_runner,
            run_dir=run_dir,
        )
        context.run_metadata.update(
            {
                "run.logs_dir": str(command_runner.logs_dir),
                "run.data_dir": str(run_dir),
                "run.target_path": str(request.target_path),
                "run.snapshot": str(snapshot_path) if snapshot_path else None,
                "sandbox.policy": self._config.sandbox.to_dict(),
                "sandbox.dry_run": request.dry_run or self._config.dry_run,
            }
        )
        agent_results: List[AgentResult] = []
        run_status = "succeeded"
        run_error: Optional[str] = None

        for agent in self._agents:
            self._logger.info("-> %s agent", agent.name)
            step_id = self._store.record_step_start(
                run_id=request.run_id,
                agent_name=agent.name,
                input_payload={
                    "prompt": request.prompt,
                    "input_docs": str(request.input_docs) if request.input_docs else None,
                    "previous_outputs": list(context.outputs),
                },
            )

            try:
                result = agent.execute(context)
                agent_results.append(result)
                context.outputs[agent.name] = result
                self._store.record_step_complete(step_id, output_payload=result.details, status=result.status)
                if result.artifacts:
                    for name, artifact in result.artifacts.items():
                        self._store.record_artifact(
                            run_id=request.run_id,
                            step_name=agent.name,
                            artifact_type=artifact.get("type", "application/json"),
                            path=artifact.get("path"),
                            payload={"name": name, "content": artifact.get("payload")},
                        )
                self._logger.info("completed %s agent with status %s", agent.name, result.status)
                self._store.record_event(
                    run_id=request.run_id,
                    event_type="agent_completed",
                    message=f"{agent.name} agent completed.",
                    payload={"status": result.status, "summary": result.summary},
                )
                if result.status != "succeeded":
                    run_status = "partial-success"
            except Exception as exc:  # pragma: no cover - defensive; surfaced via logging in tests
                run_status = "failed"
                self._logger.exception("%s agent failed: %s", agent.name, exc)
                run_error = str(exc)
                self._store.record_step_failed(step_id, error=run_error)
                self._store.record_event(
                    run_id=request.run_id,
                    event_type="agent_failed",
                    message=f"{agent.name} agent failed.",
                    payload={"error": run_error},
                )
                break

        packaging_result: Optional[PackagingResult] = None
        if run_status != "failed":
            packaging_result = self._maybe_package(request, context, agent_results)
            if packaging_result and packaging_result.status != "succeeded":
                run_status = "partial-success"
            event_type = "packaging_completed" if packaging_result else "packaging_skipped"
            self._store.record_event(
                run_id=request.run_id,
                event_type=event_type,
                message="Packaging completed." if packaging_result else "Packaging skipped (dry-run).",
                payload={
                    "packaging_path": str(packaging_result.output_path) if packaging_result else None,
                    "status": packaging_result.status if packaging_result else "skipped",
                }
                if packaging_result
                else {"reason": "dry-run"},
            )
        elif self._workspace and snapshot_path:
            restore_path = self._workspace.stage_restore(request.run_id, snapshot_path)
            if restore_path:
                self._store.record_artifact(
                    run_id=request.run_id,
                    step_name="workspace",
                    artifact_type="workspace/restore",
                    path=restore_path,
                    payload={"message": "Workspace staged for manual restore.", "path": str(restore_path)},
                )
                self._store.record_event(
                    run_id=request.run_id,
                    event_type="rollback_staged",
                    message="Workspace snapshot restored to staging directory.",
                    payload={"restore_path": str(restore_path)},
                )

        completed_at = datetime.utcnow()
        self._store.record_run_complete(
            run_id=request.run_id,
            status=run_status,
            completed_at=completed_at,
            packaging_path=packaging_result.output_path if packaging_result else None,
            error=run_error,
        )
        self._store.record_event(
            run_id=request.run_id,
            event_type="run_completed",
            message=f"Run finished with status {run_status}.",
            payload={
                "status": run_status,
                "duration_seconds": (completed_at - started_at).total_seconds(),
                "packaging_path": str(packaging_result.output_path) if packaging_result else None,
                "error": run_error,
            },
        )

        return RunResult(
            run_id=request.run_id,
            status=run_status,
            started_at=started_at,
            completed_at=completed_at,
            packaging=packaging_result,
            agent_results=agent_results,
        )

    def _maybe_package(
        self,
        request: PipelineRequest,
        context: AgentContext,
        agent_results: List[AgentResult],
    ) -> Optional[PackagingResult]:
        if self._config.dry_run or request.dry_run:
            self._logger.info("Dry-run active; skipping artifact packaging")
            return None

        metadata = {key: value for key, value in context.run_metadata.items() if value is not None}
        return self._packager.package(
            run_id=request.run_id,
            target_path=request.target_path,
            agent_results=agent_results,
            metadata=metadata,
        )
