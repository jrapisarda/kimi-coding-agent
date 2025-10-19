import json
import sqlite3
import zipfile
from pathlib import Path

from kimi_agent.agents import build_pipeline_agents
from kimi_agent.config import build_paths, load_config
from kimi_agent.orchestrator import PipelineRequest, RunController
from kimi_agent.packaging import ArtifactPackager
from kimi_agent.persistence import SQLiteRunStore
from kimi_agent.sdk import OpenAIClientFactory
from kimi_agent.workspace import WorkspaceManager


def test_run_controller_dry_run(tmp_path):
    config = load_config(path=None, dry_run=True)
    config.paths = build_paths(tmp_path)
    config.paths.data_dir.mkdir(parents=True, exist_ok=True)
    config.paths.dist_dir.mkdir(parents=True, exist_ok=True)

    store = SQLiteRunStore(config.paths.db_path)
    packager = ArtifactPackager(config.paths.dist_dir)
    agents = list(build_pipeline_agents())
    openai_client = OpenAIClientFactory.create(config.openai, dry_run=config.dry_run)
    workspace = WorkspaceManager(config.paths.data_dir)

    controller = RunController(
        config=config,
        store=store,
        agents=agents,
        packager=packager,
        workspace_manager=workspace,
    )
    target_path = tmp_path / "target"
    request = PipelineRequest(
        run_id="test-run",
        target_path=target_path,
        prompt="Test prompt",
        input_docs=None,
        dry_run=True,
    )

    result = controller.execute(request, openai_client=openai_client)
    assert result.status == "succeeded"
    assert result.packaging is None
    assert len(result.agent_results) == 4
    assert any("requirements.json" in agent.artifacts for agent in result.agent_results)
    assert not target_path.exists()
    with sqlite3.connect(config.paths.db_path) as conn:
        events = {row[0] for row in conn.execute("SELECT event_type FROM run_events")}
    assert "run_started" in events
    assert "packaging_skipped" in events


def test_run_controller_packaging(tmp_path):
    config = load_config(path=None, dry_run=False)
    config.sandbox.allow_cli_tools = True
    config.paths = build_paths(tmp_path)
    config.paths.data_dir.mkdir(parents=True, exist_ok=True)
    config.paths.dist_dir.mkdir(parents=True, exist_ok=True)

    store = SQLiteRunStore(config.paths.db_path)
    packager = ArtifactPackager(config.paths.dist_dir)
    agents = list(build_pipeline_agents())
    openai_client = OpenAIClientFactory.create(config.openai, dry_run=config.dry_run)
    workspace = WorkspaceManager(config.paths.data_dir)

    controller = RunController(
        config=config,
        store=store,
        agents=agents,
        packager=packager,
        workspace_manager=workspace,
    )
    target_path = tmp_path / "target"
    request = PipelineRequest(
        run_id="test-run-packaging",
        target_path=target_path,
        prompt="Generate a FastAPI CRUD service",
        input_docs=None,
        dry_run=False,
    )

    result = controller.execute(request, openai_client=openai_client)
    assert result.status == "succeeded"
    assert result.packaging is not None
    assert result.packaging.output_path.exists()
    assert "sbom.json" in result.packaging.files
    assert any(agent.name == "documentation" for agent in result.agent_results)
    assert (target_path / "app" / "__init__.py").exists()
    assert (target_path / "tests").exists()
    coding_agent = next(agent for agent in result.agent_results if agent.name == "coding")
    assert coding_agent.details["dependencies"]["pip"]["fastapi"] == "0.110.0"
    assert "dependencies.json" in coding_agent.artifacts
    scaffold_payload = coding_agent.artifacts["scaffold.json"]["payload"]
    assert "cli_checks" in scaffold_payload
    assert scaffold_payload["cli_checks"]
    assert scaffold_payload["cli_checks"][0]["status"] in {"skipped", "succeeded"}
    assert "resolved_manifests" in scaffold_payload
    assert scaffold_payload["resolved_manifests"]
    assert any('pip freeze' in manifest['command'] for manifest in scaffold_payload["resolved_manifests"])

    testing_agent = next(agent for agent in result.agent_results if agent.name == "testing")
    assert testing_agent.status == "succeeded"
    assert testing_agent.details["status"] == "succeeded"
    assert testing_agent.details["command"] == "python -m pytest -q"
    assert testing_agent.details["log_path"] is not None
    assert testing_agent.details.get("analysis")
    assert "test_analysis.txt" in testing_agent.artifacts

    with zipfile.ZipFile(result.packaging.output_path, "r") as archive:
        names = archive.namelist()
        assert "artifacts/documentation/CHANGELOG.md" in names
        assert any(name.startswith("logs/") for name in names)
        sbom = json.loads(archive.read("sbom.json"))
        assert "pip:fastapi==0.110.0" in sbom["dependencies"]

    with sqlite3.connect(config.paths.db_path) as conn:
        events = [row[0] for row in conn.execute("SELECT event_type FROM run_events")]
    assert "packaging_completed" in events
    assert "run_completed" in events
