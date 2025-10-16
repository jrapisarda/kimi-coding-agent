"""Typer-based CLI entrypoint."""

from __future__ import annotations

from pathlib import Path
from typing import List

import typer
from rich import print as rprint

from .config import AgentConfig, RunConfig
from .orchestrator import AgentOrchestrator

app = typer.Typer(help="Kimi multi-agent coding orchestrator")


def _default_agent_configs() -> dict:
    return {
        "requirements": AgentConfig(
            name="Requirements Agent",
            system_prompt=(
                "Distill prompts and docs into structured requirements, constraints, acceptance criteria, and risks."
            ),
        ),
        "coding": AgentConfig(
            name="Coding Agent",
            system_prompt=(
                "Produce implementation plans, shell commands, and proposed file diffs aligned with modern tooling."
            ),
        ),
        "testing": AgentConfig(
            name="Testing Agent",
            system_prompt=(
                "Author pytest 8.4 compatible tests, smoke tests, and remediation advice with deterministic strategies."
            ),
        ),
        "documentation": AgentConfig(
            name="Documentation Agent",
            system_prompt="Draft README quickstarts, commands, and limitations for the generated project.",
        ),
    }


@app.command()
def run(
    target_path: Path = typer.Argument(..., exists=True, file_okay=False, dir_okay=True, help="Workspace to modify"),
    input_docs: List[Path] = typer.Option([], "--input-docs", help="Markdown or JSON docs to ingest"),
    prompt: str = typer.Option("", "--prompt", help="User prompt"),
    enable_web_search: bool = typer.Option(False, help="Enable web search tool"),
    enable_file_search: bool = typer.Option(False, help="Enable file search tool"),
    enable_code_interpreter: bool = typer.Option(True, help="Enable code interpreter tool"),
) -> None:
    """Execute a full multi-agent run."""

    run_config = RunConfig(
        target_path=target_path,
        prompt=prompt,
        input_documents=input_docs,
        enable_web_search=enable_web_search,
        enable_file_search=enable_file_search,
        enable_code_interpreter=enable_code_interpreter,
    )

    configs = _default_agent_configs()

    orchestrator = AgentOrchestrator(
        run_config=run_config,
        requirements_config=configs["requirements"],
        coding_config=configs["coding"],
        testing_config=configs["testing"],
        documentation_config=configs["documentation"],
    )

    result = orchestrator.execute()
    rprint({
        "run_id": result.run_id,
        "summary": result.summary,
        "documentation": result.documentation.model_dump(),
    })


if __name__ == "__main__":
    app()
