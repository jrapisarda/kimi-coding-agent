from __future__ import annotations

import json
from pathlib import Path

from kimi_coding_agent.agents.coding import CodingAgent
from kimi_coding_agent.agents.documentation import DocumentationAgent
from kimi_coding_agent.agents.requirements import RequirementsAgent
from kimi_coding_agent.agents.testing import TestingAgent
from kimi_coding_agent.config import Settings
from kimi_coding_agent.orchestrator.pipeline import AgentOrchestrator
from kimi_coding_agent.persistence.store import RunStore
from kimi_coding_agent.schemas import RunConfig, RunStatus


def _write_requirements(path: Path) -> None:
    payload = {
        "requirements": [
            "Generate a Next.js dashboard skeleton.",
            "Provide pytest smoke tests.",
        ]
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_orchestrator_creates_artifacts(tmp_path):
    docs_path = tmp_path / "req.json"
    _write_requirements(docs_path)
    target_path = tmp_path / "workspace"
    state_dir = tmp_path / "state"

    settings = Settings(state_dir=state_dir)
    orchestrator = AgentOrchestrator.from_settings(
        settings,
        [RequirementsAgent(), CodingAgent(), TestingAgent(), DocumentationAgent()],
    )
    config = RunConfig(target_path=target_path, input_docs=docs_path, prompt="Create dashboard")
    result = orchestrator.execute(config)

    assert result.status is RunStatus.SUCCEEDED
    assert (target_path / "agent_plan.json").exists()
    assert (target_path / "test_plan.json").exists()
    assert (target_path / "agent_run_report.md").exists()

    dist_zip = state_dir / "dist" / f"{result.run_id}.zip"
    assert dist_zip.exists()

    store = RunStore(settings.resolve_database_path())
    stored = store.load_run(result.run_id)
    assert stored.status is RunStatus.SUCCEEDED
    assert len(stored.steps) == 4
