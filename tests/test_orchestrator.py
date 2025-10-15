from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from agentic_architect.config import Settings
from agentic_architect.models import ProjectSpecification
from agentic_architect.workflows.pipeline import AgentOrchestrator


class DummyResponse(SimpleNamespace):
    output_text: str = "Generated content"


@pytest.fixture()
def spec() -> ProjectSpecification:
    data = json.loads(Path("src/agentic_architect/examples/bioinformatics_etl_cli.json").read_text())
    return ProjectSpecification.from_json(data)


@pytest.fixture()
def orchestrator(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AgentOrchestrator:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    settings = Settings(workspace_root=tmp_path)
    orch = AgentOrchestrator(settings)

    def fake_response(self, prompt: str, *, system_prompt=None, **kwargs):  # type: ignore[no-untyped-def]
        return DummyResponse(output_text="Generated content")

    monkeypatch.setattr(type(orch._client), "create_response", fake_response)
    monkeypatch.setattr(orch._research, "search", lambda *_: [{"title": "cached"}])
    for agent in orch._agents:
        if hasattr(agent, "_initialise_git"):
            monkeypatch.setattr(agent, "_initialise_git", lambda *_args, **_kwargs: None)
    return orch


def test_orchestrator_runs_pipeline(orchestrator: AgentOrchestrator, spec: ProjectSpecification, tmp_path: Path) -> None:
    results = orchestrator.run(spec)
    project_root = tmp_path / spec.project.name.replace(" ", "-")
    assert project_root.exists()
    assert "requirements" in results
    assert "code-generation" in results
    assert (project_root / "README.md").exists()
    assert (project_root / "tests").is_dir()
