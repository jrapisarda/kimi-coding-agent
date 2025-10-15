"""Domain models for project specifications and agent context."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

import jsonschema
from pydantic import BaseModel, Field


SCHEMA_PATH = Path(__file__).parent / "json_schema" / "project_spec.schema.json"


def load_schema() -> Dict:
    """Load the JSON schema from disk."""

    with SCHEMA_PATH.open("r", encoding="utf-8") as fh:
        return json.load(fh)


class ProjectInfo(BaseModel):
    name: str
    description: str
    language: str
    package_manager: str
    license: Optional[str] = None
    repository: Optional[str] = None


class ArchitectureComponent(BaseModel):
    name: str
    responsibilities: List[str]
    dependencies: List[str] = Field(default_factory=list)


class ArchitectureSpec(BaseModel):
    pattern: str
    components: List[ArchitectureComponent]


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
        jsonschema.validate(data, schema)
        return cls.model_validate(data)


class AgentContext(BaseModel):
    """Shared context passed between agents."""

    specification: ProjectSpecification
    workspace_root: Path
    assumptions: List[str] = Field(default_factory=list)
    generated_paths: List[Path] = Field(default_factory=list)
    metadata: Dict[str, str] = Field(default_factory=dict)


__all__ = ["ProjectSpecification", "AgentContext"]
