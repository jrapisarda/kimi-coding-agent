from __future__ import annotations

import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import click

from .agents import build_pipeline_agents
from .config import AppConfig, load_config
from .logging_config import configure_logging
from .orchestrator import PipelineRequest, RunController
from .packaging import ArtifactPackager
from .persistence import SQLiteRunStore
from .sdk import OpenAIClientFactory
from .workspace import WorkspaceManager


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(message="Kimi Agent CLI %(version)s")
def main() -> None:
    """Local-first multi-agent coding assistant."""


@main.command()
@click.argument("target_path", type=click.Path(path_type=Path))
@click.option("--input-docs", type=click.Path(exists=False, path_type=Path), default=None)
@click.option("--prompt", type=str, default=None, help="Optional free-form instructions for the run.")
@click.option("--config", "config_path", type=click.Path(exists=True, path_type=Path), default=None)
@click.option("--dry-run", is_flag=True, default=False, help="Execute without modifying the target project.")
@click.option("--verbose", is_flag=True, default=False, help="Increase logging verbosity.")
@click.option("--run-id", type=str, default=None, help="Override generated run identifier.")
@click.option("--allow-cli-tools", is_flag=True, default=False, help="Permit CLI scaffolding commands (e.g. npm create).")
@click.option("--allow-package-installs", is_flag=True, default=False, help="Permit package installation commands (e.g. pip install).")
def run(  # pragma: no cover - thin CLI wrapper exercised via integration tests
    target_path: Path,
    input_docs: Optional[Path],
    prompt: Optional[str],
    config_path: Optional[Path],
    dry_run: bool,
    verbose: bool,
    run_id: Optional[str],
    allow_cli_tools: bool,
    allow_package_installs: bool,
) -> None:
    """Execute the multi-agent pipeline (Requirements -> Coding -> Testing -> Documentation)."""

    logger = configure_logging(verbose=verbose, logger_name="kimi_agent.cli")

    app_config = _prepare_config(
        config_path=config_path,
        dry_run=dry_run,
        allow_cli_tools=allow_cli_tools,
        allow_package_installs=allow_package_installs,
    )
    store = SQLiteRunStore(app_config.paths.db_path)
    packager = ArtifactPackager(app_config.paths.dist_dir)
    agents = list(build_pipeline_agents())
    openai_client = OpenAIClientFactory.create(app_config.openai, dry_run=app_config.dry_run)
    workspace = WorkspaceManager(app_config.paths.data_dir)

    controller = RunController(
        config=app_config,
        store=store,
        agents=agents,
        packager=packager,
        workspace_manager=workspace,
    )

    request = PipelineRequest(
        run_id=run_id or _generate_run_id(),
        target_path=target_path.resolve(),
        prompt=prompt,
        input_docs=input_docs.resolve() if input_docs else None,
        dry_run=dry_run,
    )

    logger.info("Run ID: %s", request.run_id)
    if prompt:
        logger.info("Prompt: %s", prompt)
    if input_docs:
        logger.info("Input docs: %s", input_docs)

    result = controller.execute(request, openai_client=openai_client)
    _print_summary(result)
    if result.status == "failed":
        sys.exit(1)


def _prepare_config(
    config_path: Optional[Path],
    dry_run: bool,
    allow_cli_tools: bool,
    allow_package_installs: bool,
) -> AppConfig:
    config = load_config(config_path, dry_run=dry_run)
    if allow_cli_tools:
        config.sandbox.allow_cli_tools = True
    if allow_package_installs:
        config.sandbox.allow_package_installs = True
    config.paths.data_dir.mkdir(parents=True, exist_ok=True)
    config.paths.dist_dir.mkdir(parents=True, exist_ok=True)
    return config


def _generate_run_id() -> str:
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    suffix = uuid.uuid4().hex[:6]
    return f"run-{timestamp}-{suffix}"


def _print_summary(result) -> None:
    click.echo("")
    click.echo(click.style(f"Run {result.run_id} status: {result.status}", fg="green" if result.status == "succeeded" else "yellow"))
    for agent_result in result.agent_results:
        click.echo(f" - {agent_result.name}: {agent_result.status} :: {agent_result.summary}")
    if result.packaging:
        click.echo(f"Package: {result.packaging.output_path}")
