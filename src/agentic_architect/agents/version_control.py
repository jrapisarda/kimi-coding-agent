"""Version control agent handling git workflows."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Dict

from ..models import AgentContext
from .base import BaseAgent


class VersionControlAgent(BaseAgent):
    """Initialises git repository and branch strategy."""

    system_prompt = "You are a DevOps engineer configuring git workflows."

    def __init__(self, client, session_factory) -> None:  # type: ignore[no-untyped-def]
        super().__init__("version-control", client, session_factory)

    def execute(self, context: AgentContext) -> Dict[str, Any]:
        spec = context.specification
        project_root = context.workspace_root / spec.project.name.replace(" ", "-")
        self._initialise_git(project_root)
        self._create_branch_docs(project_root)
        return {"git_repo": str(project_root / ".git")}

    def _initialise_git(self, path: Path) -> None:
        if (path / ".git").exists():
            return
        subprocess.run(["git", "init"], cwd=path, check=False)
        gitignore = path / ".gitignore"
        gitignore.write_text(self._gitignore_content(), encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=path, check=False)
        subprocess.run(["git", "commit", "-m", "chore: initial scaffold"], cwd=path, check=False)

    def _create_branch_docs(self, path: Path) -> None:
        docs = path / "docs"
        docs.mkdir(exist_ok=True)
        strategy = docs / "BRANCHING.md"
        strategy.write_text(self._branching_strategy(), encoding="utf-8")

    def _gitignore_content(self) -> str:
        return (
            "__pycache__/\n"
            "*.pyc\n"
            ".python-version\n"
            "venv/\n"
            ".mypy_cache/\n"
            ".pytest_cache/\n"
            "coverage.xml\n"
        )

    def _branching_strategy(self) -> str:
        return (
            "# Branch Strategy\n"
            "- main: production-ready releases\n"
            "- develop: integration branch\n"
            "- feature/*: feature development\n"
            "- hotfix/*: urgent fixes\n"
        )


__all__ = ["VersionControlAgent"]
