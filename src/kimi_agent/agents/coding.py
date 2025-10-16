"""Coding agent definition."""

from __future__ import annotations

from typing import Any, Dict

from pydantic import Field

from .base import AgentOutput, BasePersonaAgent


class CodingOutput(AgentOutput):
    """Structured plan for code generation."""

    tasks: list[str] = Field(default_factory=list, description="Ordered list of coding tasks")
    commands: list[str] = Field(default_factory=list, description="Shell commands to execute")
    files: dict[str, str] = Field(default_factory=dict, description="Mapping of file paths to proposed contents")
    dependencies: list[str] = Field(default_factory=list, description="Dependencies to add")


class CodingAgent(BasePersonaAgent):
    """Persona that plans code changes and tool invocations."""

    def build_input(self, context: Dict[str, Any]) -> str:
        requirements: Dict[str, Any] = context.get("requirements", {})
        return (
            "You are the Coding Agent. Produce a concise implementation plan, explicit shell commands, and proposed file diffs. "
            "Use deterministic seeds and prefer local execution."
            f"\n\nRequirements JSON:\n{requirements}"
        )
