"""CLI entrypoint implementing `agent run`."""

import logging
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

from ..agents.coding import CodingAgent
from ..agents.documentation import DocumentationAgent
from ..agents.requirements import RequirementsAgent
from ..agents.testing import TestingAgent
from ..config import DEFAULT_SETTINGS, Settings
from ..orchestrator.pipeline import AgentOrchestrator
from ..schemas import RunConfig, RunStatus

console = Console()


def _build_orchestrator(settings: Settings) -> AgentOrchestrator:
    agents = [
        RequirementsAgent(),
        CodingAgent(),
        TestingAgent(),
        DocumentationAgent(),
    ]
    return AgentOrchestrator.from_settings(settings, agents)


@click.group()
def app() -> None:
    """Local-first multi-agent coding orchestrator."""


@app.command("run")
@click.argument("target_path", type=click.Path(path_type=Path))
@click.option(
    "--input-docs",
    type=click.Path(path_type=Path),
    default=None,
    help="Path to Markdown/JSON requirements.",
)
@click.option("--prompt", type=str, default=None, help="Inline description of desired project.")
@click.option(
    "--state-dir",
    type=click.Path(path_type=Path),
    default=None,
    help="Override location for state and artifacts.",
)
def run_command(
    target_path: Path,
    input_docs: Optional[Path],
    prompt: Optional[str],
    state_dir: Optional[Path],
) -> None:
    """Execute the orchestrated agent pipeline."""

    logging.basicConfig(level=logging.INFO)
    settings = DEFAULT_SETTINGS if state_dir is None else Settings(state_dir=state_dir)
    orchestrator = _build_orchestrator(settings)
    config = RunConfig(target_path=target_path, input_docs=input_docs, prompt=prompt)
    result = orchestrator.execute(config)

    table = Table(title="Agent Run Summary", show_lines=True)
    table.add_column("Agent")
    table.add_column("Status")
    table.add_column("Details")

    for step in result.steps:
        details = step.payload.get("summary") if isinstance(step.payload, dict) else ""
        table.add_row(step.agent_name, step.status.value, details or "")

    console.print(table)
    console.print(f"Run ID: {result.run_id}")
    console.print(f"Status: {result.status.value}")

    if result.status is not RunStatus.SUCCEEDED:
        raise SystemExit(1)


if __name__ == "__main__":  # pragma: no cover
    app()
