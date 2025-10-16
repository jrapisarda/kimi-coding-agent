"""Shared data models for the Kimi coding agent system."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class RunStatus(str, Enum):
    """Lifecycle states tracked for an agent run."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class RunConfig(BaseModel):
    """CLI-supplied configuration that kicks off a pipeline execution."""

    target_path: Path = Field(..., description="Workspace where generated assets are written.")
    input_docs: Optional[Path] = Field(
        default=None,
        description="Optional directory or file providing additional requirements in Markdown or JSON.",
    )
    prompt: Optional[str] = Field(
        default=None,
        description="Optional free-form text describing the desired project.",
    )


class InputDocument(BaseModel):
    """Materialized representation of an input document consumed by the Requirements agent."""

    source_path: Optional[Path] = Field(default=None)
    content: str = Field(...)
    content_type: str = Field(...)


class RequirementsContext(BaseModel):
    """Structured output emitted by the Requirements agent."""

    summary: str = Field(...)
    structured_requirements: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    documents: List[InputDocument] = Field(default_factory=list)
    raw_prompt: Optional[str] = Field(default=None)


class CodingContext(BaseModel):
    """Description of the coding plan and generated assets."""

    plan: List[str] = Field(default_factory=list)
    generated_files: List[Path] = Field(default_factory=list)
    dependency_notes: List[str] = Field(default_factory=list)
    summary: str = Field(default="Coding plan generated.")


class TestingContext(BaseModel):
    """Results gathered by the Testing agent."""

    tests_run: List[str] = Field(default_factory=list)
    status: str = Field(default="not_run")
    summary: str = Field(default="No tests executed.")


class DocumentationContext(BaseModel):
    """Documentation artifacts prepared by the Documentation agent."""

    readme_path: Optional[Path] = Field(default=None)
    summary: str = Field(default="")
    additional_notes: Dict[str, Any] = Field(default_factory=dict)


class AgentStepResult(BaseModel):
    """Envelope persisted for each agent step."""

    agent_name: str
    started_at: datetime
    completed_at: datetime
    status: RunStatus
    payload: Dict[str, Any] = Field(default_factory=dict)


class RunResult(BaseModel):
    """Finalized result that aggregates agent outputs."""

    run_id: str
    status: RunStatus
    started_at: datetime
    completed_at: datetime
    steps: List[AgentStepResult]
    contexts: Dict[str, Any] = Field(default_factory=dict)
