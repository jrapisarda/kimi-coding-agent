"""Documentation agent generating README and API docs."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from ..models import AgentContext
from .base import BaseAgent


class DocumentationAgent(BaseAgent):
    """Creates README and documentation placeholders."""

    system_prompt = "You are a technical writer producing high quality documentation."

    def __init__(self, client, session_factory) -> None:  # type: ignore[no-untyped-def]
        super().__init__("documentation", client, session_factory)

    def execute(self, context: AgentContext) -> Dict[str, Any]:
        spec = context.specification
        project_root = context.workspace_root / spec.project.name.replace(" ", "-")
        readme = project_root / "README.md"
        readme.write_text(self._generate_readme(spec, context.assumptions), encoding="utf-8")
        docs_dir = project_root / "docs"
        docs_dir.mkdir(exist_ok=True)
        api_doc = docs_dir / "API.md"
        api_doc.write_text(self._generate_api_doc(spec), encoding="utf-8")
        context.generated_paths.extend([readme, docs_dir, api_doc])
        return {"readme": str(readme), "api_doc": str(api_doc)}

    def _generate_readme(self, spec, assumptions):  # type: ignore[no-untyped-def]
        sections = [
            f"# {spec.project.name}\n",
            f"{spec.project.description}\n",
            "## Getting Started\n",
            "```bash\nmake install\nmake test\n```\n",
            "## Quality Tooling\n",
            "- black\n- ruff\n- mypy\n- bandit\n- safety\n",
            "## Assumptions\n",
        ]
        if assumptions:
            sections.extend(f"- {item}\n" for item in assumptions)
        else:
            sections.append("- No additional assumptions\n")

        deliverables = spec.deliverables.final_package
        if deliverables.required_files or deliverables.metadata_includes:
            sections.append("\n## Final Package Deliverables\n")
            if deliverables.required_files:
                sections.extend(f"- {item}\n" for item in deliverables.required_files)
            if deliverables.metadata_includes:
                sections.append("\n### Metadata\n")
                sections.extend(f"- {item}\n" for item in deliverables.metadata_includes)
            if deliverables.packaging_format:
                sections.append(f"\nPreferred packaging: {deliverables.packaging_format}\n")

        return "\n".join(sections)

    def _generate_api_doc(self, spec) -> str:  # type: ignore[no-untyped-def]
        sections = ["# API Documentation", "Generated endpoints and modules will be documented here."]
        for component in spec.architecture.components:
            sections.append(f"## {component.name}\nResponsibilities:\n")
            sections.extend(f"- {resp}" for resp in component.responsibilities)
        return "\n\n".join(sections)


__all__ = ["DocumentationAgent"]
