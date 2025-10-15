"""Domain models for project specifications and agent context."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import jsonschema
from pydantic import BaseModel, Field


SCHEMA_PATH = Path(__file__).parent / "json_schema" / "project_spec.schema.json"


def load_schema() -> Dict:
    """Load the JSON schema from disk."""

    with SCHEMA_PATH.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _ensure_list(value: Any) -> List[str]:
    """Coerce a value into a list of strings."""

    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def _drop_none(values: Dict[str, Any]) -> Dict[str, Any]:
    """Remove keys whose values are ``None`` to satisfy JSON schema constraints."""

    return {key: value for key, value in values.items() if value is not None}


def _parse_coverage_threshold(value: Any) -> float:
    """Normalize coverage thresholds expressed as decimals or percentages."""

    if isinstance(value, (int, float)):
        numeric = float(value)
        return numeric / 100 if numeric > 1 else numeric
    if isinstance(value, str):
        match = re.search(r"(\d+(?:\.\d+)?)", value)
        if match:
            numeric = float(match.group(1))
            return numeric / 100 if numeric > 1 else numeric
    return 0.8


def _normalize_architecture(specifications: Dict[str, Any]) -> Dict[str, Any]:
    architecture = specifications.get("architecture", {}) if specifications else {}
    components: List[Dict[str, Any]] = []

    for index, component in enumerate(architecture.get("components", [])):
        if isinstance(component, str):
            components.append(
                {
                    "name": component,
                    "responsibilities": [],
                    "dependencies": [],
                }
            )
        elif isinstance(component, dict):
            name = component.get("name") or f"component-{index + 1}"
            components.append(
                {
                    "name": name,
                    "responsibilities": _ensure_list(component.get("responsibilities")),
                    "dependencies": _ensure_list(component.get("dependencies")),
                }
            )

    return {
        "pattern": architecture.get("pattern", "unspecified"),
        "components": components,
    }


def _normalize_tasks(tasks: Optional[List[Dict[str, Any]]], specifications: Dict[str, Any]) -> List[Dict[str, Any]]:
    if tasks:
        normalized_tasks: List[Dict[str, Any]] = []
        for task in tasks:
            if not isinstance(task, dict):
                continue
            normalized_tasks.append(
                {
                    "id": task.get("id", f"TASK-{len(normalized_tasks) + 1:03d}"),
                    "description": task.get("description", ""),
                    "deliverables": _ensure_list(task.get("deliverables")),
                    "priority": task.get("priority"),
                }
            )
        if normalized_tasks:
            return normalized_tasks

    functional = specifications.get("functional_requirements", {}) if specifications else {}
    core_features = functional.get("core_features", [])
    generated_tasks = [
        {
            "id": f"FR-{index + 1:03d}",
            "description": str(feature),
            "deliverables": [],
        }
        for index, feature in enumerate(core_features)
    ]
    if generated_tasks:
        return generated_tasks

    return [
        {
            "id": "INIT-001",
            "description": "Initial project scaffolding",
            "deliverables": [],
        }
    ]


def _normalize_testing(testing: Optional[Dict[str, Any]], quality_assurance: Dict[str, Any]) -> Dict[str, Any]:
    if testing:
        return {
            "coverage_threshold": _parse_coverage_threshold(testing.get("coverage_threshold", 0.8)),
            "test_types": _ensure_list(testing.get("test_types")),
            "integration_requirements": _ensure_list(testing.get("integration_requirements")),
        }

    testing_strategy = (quality_assurance or {}).get("testing_strategy", {})
    test_types: List[str] = []
    for key in ("unit_tests", "integration_tests", "acceptance_tests"):
        test_types.extend(_ensure_list(testing_strategy.get(key)))

    coverage_value = _parse_coverage_threshold(
        (quality_assurance or {}).get("code_quality", {}).get("coverage_target")
    )

    return {
        "coverage_threshold": coverage_value,
        "test_types": test_types or ["unit"],
        "integration_requirements": [],
    }


def _normalize_documentation(
    documentation: Optional[Dict[str, Any]],
    specifications: Dict[str, Any],
    project: Dict[str, Any],
) -> Dict[str, Any]:
    if documentation:
        return _drop_none(
            {
                "audience": documentation.get("audience", project.get("type", "engineering")),
                "artifacts": _ensure_list(documentation.get("artifacts")),
                "style_guide": documentation.get("style_guide"),
            }
        )

    functional = specifications.get("functional_requirements", {}) if specifications else {}
    documentation_agent = functional.get("documentation_agent")
    if isinstance(documentation_agent, dict):
        artifacts = _ensure_list(documentation_agent.get("output"))
    else:
        artifacts = []

    return _drop_none(
        {
            "audience": project.get("type", "engineering"),
            "artifacts": artifacts or ["README"],
            "style_guide": None,
        }
    )


def _normalize_quality(quality: Optional[Dict[str, Any]], quality_assurance: Dict[str, Any]) -> Dict[str, Any]:
    if quality:
        return _drop_none(
            {
                "formatters": _ensure_list(quality.get("formatters")),
                "linters": _ensure_list(quality.get("linters")),
                "type_checking": quality.get("type_checking"),
            }
        )

    code_quality = (quality_assurance or {}).get("code_quality", {})
    return _drop_none(
        {
            "formatters": _ensure_list(code_quality.get("formatting")),
            "linters": _ensure_list(code_quality.get("linting")),
            "type_checking": code_quality.get("type_checking"),
        }
    )


def _normalize_deployment(deployment: Optional[Dict[str, Any]], specifications: Dict[str, Any]) -> Dict[str, Any]:
    if deployment:
        return {
            "targets": _ensure_list(deployment.get("targets")),
            "ci_cd": _ensure_list(deployment.get("ci_cd")),
        }

    architecture = (specifications or {}).get("architecture", {})
    deployment_target = architecture.get("deployment")
    targets = _ensure_list(deployment_target) if deployment_target else []
    return {
        "targets": targets,
        "ci_cd": [],
    }


def normalize_specification_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Transform flexible requirement formats into the canonical schema."""

    if {"architecture", "tasks", "testing", "documentation"}.issubset(data.keys()):
        return data

    project = data.get("project", {})
    specifications = data.get("specifications", {})
    quality_assurance = data.get("quality_assurance", {})

    normalized_project = {
        key: value
        for key, value in {
            "name": project.get("name", "unnamed-project"),
            "description": project.get("description", ""),
            "language": project.get("language")
            or project.get("primary_language")
            or "python",
            "package_manager": project.get("package_manager", "pip"),
            "license": project.get("license"),
            "repository": project.get("repository"),
            "version": project.get("version"),
            "type": project.get("type"),
            "complexity": project.get("complexity"),
        }.items()
        if value is not None
    }

    return {
        "project": normalized_project,
        "architecture": _normalize_architecture(specifications),
        "tasks": _normalize_tasks(data.get("tasks"), specifications),
        "testing": _normalize_testing(data.get("testing"), quality_assurance),
        "documentation": _normalize_documentation(data.get("documentation"), specifications, project),
        "quality": _normalize_quality(data.get("quality"), quality_assurance),
        "deployment": _normalize_deployment(data.get("deployment"), specifications),
    }


class ProjectInfo(BaseModel):
    name: str
    description: str
    language: str = "python"
    package_manager: str = "pip"
    license: Optional[str] = None
    repository: Optional[str] = None
    version: Optional[str] = None
    type: Optional[str] = None
    complexity: Optional[str] = None


class ArchitectureComponent(BaseModel):
    name: str
    responsibilities: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)


class ArchitectureSpec(BaseModel):
    pattern: str
    components: List[ArchitectureComponent] = Field(default_factory=list)


class TaskSpec(BaseModel):
    id: str
    description: str
    deliverables: List[str]
    priority: Optional[str] = None


class TestingSpec(BaseModel):
    coverage_threshold: float
    test_types: List[str]
    integration_requirements: List[str] = Field(default_factory=list)


class DocumentationSpec(BaseModel):
    audience: str
    artifacts: List[str]
    style_guide: Optional[str] = None


class QualitySpec(BaseModel):
    formatters: List[str] = Field(default_factory=list)
    linters: List[str] = Field(default_factory=list)
    type_checking: Optional[str] = None


class DeploymentSpec(BaseModel):
    targets: List[str] = Field(default_factory=list)
    ci_cd: List[str] = Field(default_factory=list)


class ProjectSpecification(BaseModel):
    project: ProjectInfo
    architecture: ArchitectureSpec
    tasks: List[TaskSpec]
    testing: TestingSpec
    documentation: DocumentationSpec
    quality: QualitySpec = Field(default_factory=QualitySpec)
    deployment: DeploymentSpec = Field(default_factory=DeploymentSpec)

    @classmethod
    def from_json(cls, data: Dict) -> "ProjectSpecification":
        """Validate JSON data against schema and return specification."""

        schema = load_schema()
        normalized = normalize_specification_data(data)
        jsonschema.validate(normalized, schema)
        return cls.model_validate(normalized)


class AgentContext(BaseModel):
    """Shared context passed between agents."""

    specification: ProjectSpecification
    workspace_root: Path
    assumptions: List[str] = Field(default_factory=list)
    generated_paths: List[Path] = Field(default_factory=list)
    metadata: Dict[str, str] = Field(default_factory=dict)


__all__ = ["ProjectSpecification", "AgentContext"]
