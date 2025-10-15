"""Testing agent responsible for generating and configuring tests."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from ..models import AgentContext
from .base import BaseAgent


class TestingAgent(BaseAgent):
    """Produces pytest scaffolding and coverage configuration."""

    system_prompt = "You are a senior QA engineer designing comprehensive tests."

    def __init__(self, client, session_factory) -> None:  # type: ignore[no-untyped-def]
        super().__init__("testing", client, session_factory)

    def execute(self, context: AgentContext) -> Dict[str, Any]:
        spec = context.specification
        project_root = context.workspace_root / spec.project.name.replace(" ", "-")
        tests_dir = project_root / "tests"
        tests_dir.mkdir(parents=True, exist_ok=True)
        context.generated_paths.append(tests_dir)

        coverage_config = project_root / ".coveragerc"
        coverage_config.write_text(self._coverage_template(spec.testing.coverage_threshold), encoding="utf-8")

        pytest_ini = project_root / "pytest.ini"
        pytest_ini.write_text(self._pytest_ini_content(), encoding="utf-8")

        test_plan_path = tests_dir / "test_plan.md"
        test_plan_path.write_text(
            self._test_plan(spec.testing.test_types, spec.deliverables.final_package.required_files),
            encoding="utf-8",
        )

        return {
            "tests_dir": str(tests_dir),
            "coverage_config": str(coverage_config),
            "pytest_ini": str(pytest_ini),
        }

    def _coverage_template(self, threshold: float) -> str:
        return (
            "[run]\n"
            "branch = True\n"
            "source = src\n\n"
            "[report]\n"
            f"fail_under = {threshold * 100:.0f}\n"
        )

    def _pytest_ini_content(self) -> str:
        return (
            "[pytest]\n"
            "addopts = -ra --strict-markers --maxfail=1\n"
            "testpaths = tests\n"
        )

    def _test_plan(self, test_types: List[str], deliverables: List[str]) -> str:
        sections = ["# Test Plan"]
        for test_type in test_types:
            sections.append(f"## {test_type.title()} Tests\n- Pending implementation")
        if deliverables:
            sections.append("## Deliverables Verification")
            sections.extend(f"- Confirm {item} is produced" for item in deliverables)
        return "\n\n".join(sections)


__all__ = ["TestingAgent"]
