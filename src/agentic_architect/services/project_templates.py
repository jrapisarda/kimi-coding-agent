"""Template selection utilities for well-known project archetypes."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from ..models import ProjectSpecification


@dataclass(frozen=True)
class ProjectTemplate:
    """Represents a reusable scaffold for a project archetype."""

    key: str
    description: str
    directories: List[str]
    files: Dict[str, str]

    def render_plan(self, spec: ProjectSpecification) -> str:
        """Produce a human readable plan for the selected template."""

        deliverables = spec.deliverables.final_package.required_files or [
            "Define deliverable assets",
        ]

        sections: List[str] = [
            f"# {spec.project.name} Delivery Blueprint",
            f"Template: {self.description}",
            "## Deliverables Checklist",
        ]
        sections.extend(f"- {item}" for item in deliverables)

        sections.append("\n## Core Directory Layout")
        sections.extend(f"- {directory}" for directory in self.directories)

        if self.files:
            sections.append("\n## Stub Files")
            sections.extend(f"- {path}" for path in self.files)

        sections.append("\n## Implementation Notes")
        sections.append(
            "This template ensures the agent pipeline materialises the deliverables required "
            "for downstream verification. Extend each module with concrete business logic and "
            "tests tailored to the specification."
        )

        return "\n".join(sections)


def _etl_template() -> ProjectTemplate:
    return ProjectTemplate(
        key="etl",
        description="Batch and streaming ETL data platform",
        directories=[
            "src/etl", "src/pipelines", "config", "migrations", "tests/unit", "tests/integration",
        ],
        files={
            "src/etl/__init__.py": "",
            "src/pipelines/__init__.py": "",
            "config/settings.toml": "# ETL settings placeholder\n",
            "migrations/README.md": "# Migration notes\n",
        },
    )


def _ai_ml_template() -> ProjectTemplate:
    return ProjectTemplate(
        key="ai-ml",
        description="AI/ML microservices with async workers",
        directories=[
            "services/api_gateway",
            "services/model_service",
            "services/worker",
            "services/feature_store",
            "infrastructure",
            "frontend",
            "tests/services",
            "tests/integration",
        ],
        files={
            "services/api_gateway/__init__.py": "",
            "services/model_service/__init__.py": "",
            "services/worker/tasks.py": "# Worker task stubs\n",
            "services/feature_store/__init__.py": "",
            "infrastructure/README.md": "# Infrastructure automation notes\n",
        },
    )


def _webapp_template() -> ProjectTemplate:
    return ProjectTemplate(
        key="webapp",
        description="Full-stack web application with API and frontend",
        directories=[
            "src/api",
            "src/core",
            "src/web",
            "public",
            "tests/e2e",
            "tests/unit",
        ],
        files={
            "src/api/__init__.py": "",
            "src/core/__init__.py": "",
            "src/web/__init__.py": "",
            "src/web/routes.py": "# Web routes placeholder\n",
            "public/README.md": "# Static assets description\n",
        },
    )


TEMPLATES: Dict[str, ProjectTemplate] = {
    "etl": _etl_template(),
    "ai-ml": _ai_ml_template(),
    "webapp": _webapp_template(),
}


def _matches_any(text: str, keywords: Iterable[str]) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in keywords)


def select_template(spec: ProjectSpecification) -> Optional[ProjectTemplate]:
    """Select the most appropriate template for the project specification."""

    project_type = (spec.project.type or "").lower()
    descriptor = " ".join(
        [
            spec.project.name,
            spec.project.description,
            project_type,
            spec.architecture.pattern,
        ]
    )

    if _matches_any(project_type, ["etl", "data-pipeline"]) or _matches_any(
        descriptor, ["etl", "data pipeline", "ingestion", "extraction"]
    ):
        return TEMPLATES["etl"]

    if _matches_any(project_type, ["ai", "ml", "machine-learning"]) or _matches_any(
        descriptor, ["ai", "ml", "model", "microservice", "inference"]
    ):
        return TEMPLATES["ai-ml"]

    if _matches_any(project_type, ["web", "webapp", "frontend"]) or _matches_any(
        descriptor, ["web", "frontend", "next.js", "react", "spa"]
    ):
        return TEMPLATES["webapp"]

    return None


def materialise_template(project_root: Path, spec: ProjectSpecification, template: ProjectTemplate) -> None:
    """Create directories and stub files for the selected template."""

    for directory in template.directories:
        path = project_root / directory
        path.mkdir(parents=True, exist_ok=True)

    for relative_path, content in template.files.items():
        target = project_root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        if content:
            target.write_text(content, encoding="utf-8")
        else:
            target.touch()


__all__ = ["ProjectTemplate", "select_template", "materialise_template"]

