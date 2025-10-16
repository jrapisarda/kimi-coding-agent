"""Documentation agent implementation."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from ..schemas import (
    CodingContext,
    DocumentationContext,
    RequirementsContext,
    RunConfig,
    TestingContext,
)
from .base import BaseAgent


class DocumentationAgent(BaseAgent):
    """Produces human-readable run documentation."""

    def __init__(self) -> None:
        super().__init__(name="documentation")

    def run(self, *, config: RunConfig, shared_state: Dict[str, Any]) -> Dict[str, Any]:
        requirements = RequirementsContext.model_validate(shared_state.get("requirements", {}))
        coding = CodingContext.model_validate(shared_state.get("coding", {}))
        testing = TestingContext.model_validate(shared_state.get("testing", {}))

        readme_path = config.target_path / "agent_run_report.md"
        readme_path.write_text(_render_report(requirements, coding, testing), encoding="utf-8")

        context = DocumentationContext(
            readme_path=readme_path,
            summary="Run documentation generated.",
            additional_notes={
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        shared_state[self.name] = context.model_dump()
        return context.model_dump()


def _render_report(
    requirements: RequirementsContext,
    coding: CodingContext,
    testing: TestingContext,
) -> str:
    sections: List[str] = []
    sections.append("# Agent Run Report\n")
    sections.append("## Requirements Summary\n")
    sections.append(f"{requirements.summary}\n\n")
    if requirements.structured_requirements:
        sections.append("### Structured Requirements\n")
        for item in requirements.structured_requirements:
            sections.append(f"- {item}\n")
        sections.append("\n")
    if requirements.assumptions:
        sections.append("### Assumptions\n")
        for assumption in requirements.assumptions:
            sections.append(f"- {assumption}\n")
        sections.append("\n")

    sections.append("## Coding Plan\n")
    for line in coding.plan:
        sections.append(f"- {line}\n")
    sections.append("\n")

    sections.append("## Dependency Notes\n")
    for note in coding.dependency_notes:
        sections.append(f"- {note}\n")
    sections.append("\n")

    sections.append("## Testing Summary\n")
    sections.append(f"Status: {testing.status}\n\n")
    sections.append(f"{testing.summary}\n\n")
    if testing.tests_run:
        sections.append("### Commands\n")
        for cmd in testing.tests_run:
            sections.append(f"- {cmd}\n")
        sections.append("\n")

    sections.append("## Provenance\n")
    sections.append(f"Generated at: {datetime.now(timezone.utc).isoformat()}\n")

    return "".join(sections)
