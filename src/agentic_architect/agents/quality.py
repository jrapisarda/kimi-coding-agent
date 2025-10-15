"""Quality assurance agent configuring tooling and reports."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from ..models import AgentContext
from .base import BaseAgent


class QualityAssuranceAgent(BaseAgent):
    """Sets up formatting, linting, type checking, and security scanning."""

    system_prompt = "You are responsible for enforcing code quality and compliance."

    def __init__(self, client, session_factory) -> None:  # type: ignore[no-untyped-def]
        super().__init__("quality", client, session_factory)

    def execute(self, context: AgentContext) -> Dict[str, Any]:
        spec = context.specification
        project_root = context.workspace_root / spec.project.name.replace(" ", "-")
        pre_commit = project_root / ".pre-commit-config.yaml"
        pre_commit.write_text(self._pre_commit_config(), encoding="utf-8")
        makefile = project_root / "Makefile"
        makefile.write_text(self._makefile_contents(), encoding="utf-8")
        context.generated_paths.extend([pre_commit, makefile])
        return {"pre_commit": str(pre_commit), "makefile": str(makefile)}

    def _pre_commit_config(self) -> str:
        return (
            "repos:\n"
            "  - repo: https://github.com/psf/black\n"
            "    rev: 24.10.0\n"
            "    hooks:\n"
            "      - id: black\n"
            "  - repo: https://github.com/astral-sh/ruff-pre-commit\n"
            "    rev: v0.7.4\n"
            "    hooks:\n"
            "      - id: ruff\n"
            "      - id: ruff-format\n"
            "  - repo: https://github.com/pre-commit/mirrors-mypy\n"
            "    rev: v1.13.0\n"
            "    hooks:\n"
            "      - id: mypy\n"
            "  - repo: https://github.com/PyCQA/bandit\n"
            "    rev: 1.7.9\n"
            "    hooks:\n"
            "      - id: bandit\n"
        )

    def _makefile_contents(self) -> str:
        return (
            "install:\n"
            "\tpip install -e .[dev]\n\n"
            "format:\n"
            "\tblack .\n\truff check --fix .\n\n"
            "lint:\n"
            "\truff check .\n\tmypy src\n\tbandit -r src\n\tsafety check\n\n"
            "test:\n"
            "\tpytest\n\n"
            "ci:\n"
            "\tpytest --cov=agentic_architect --cov-report=xml\n"
        )


__all__ = ["QualityAssuranceAgent"]
