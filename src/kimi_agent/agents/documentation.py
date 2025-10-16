"""Documentation agent definition."""

from __future__ import annotations

from typing import Any, Dict

from pydantic import Field

from .base import AgentOutput, BasePersonaAgent


class DocumentationOutput(AgentOutput):
    """Structured README draft and changelog."""

    quickstart: str = Field(..., description="Quickstart instructions")
    commands: list[str] = Field(default_factory=list, description="Important commands to surface")
    limitations: list[str] = Field(default_factory=list, description="Known limitations")


class DocumentationAgent(BasePersonaAgent):
    """Persona that generates documentation."""

    def build_input(self, context: Dict[str, Any]) -> str:
        summary = context.get("summary", "")
        testing = context.get("testing", {})
        return (
            "You are the Documentation Agent. Produce a README section with quickstart steps, key commands, reproducibility note"
            "s, and known limitations."
            f"\n\nRun Summary:\n{summary}\n\nTesting JSON:\n{testing}"
        )
