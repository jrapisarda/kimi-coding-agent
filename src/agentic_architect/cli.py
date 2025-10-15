"""Command line interface for the agentic architect."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer

from .config import Settings
from .models import ProjectSpecification
from .workflows.pipeline import AgentOrchestrator

app = typer.Typer(help="Generate complete projects from JSON specifications")


@app.command()
def generate(
    spec_path: Path = typer.Argument(..., exists=True, readable=True, help="Path to the JSON specification"),
    workspace: Optional[Path] = typer.Option(None, "--workspace", help="Workspace root for project output"),
) -> None:
    """Generate a project using the orchestrator."""

    data = json.loads(spec_path.read_text(encoding="utf-8"))
    spec = ProjectSpecification.from_json(data)
    settings = Settings(workspace_root=workspace or Path.cwd())
    orchestrator = AgentOrchestrator(settings)
    orchestrator.run(spec)
    typer.echo("Project generation complete")


__all__ = ["app", "generate"]
