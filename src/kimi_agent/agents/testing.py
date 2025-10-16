"""Testing agent definition."""

from __future__ import annotations

from typing import Any, Dict

from pydantic import Field

from .base import AgentOutput, BasePersonaAgent


class TestingOutput(AgentOutput):
    """Structured test instructions."""

    tests: list[str] = Field(default_factory=list, description="Test cases to generate")
    commands: list[str] = Field(default_factory=list, description="Commands to run tests")
    remediation: list[str] = Field(default_factory=list, description="Steps to resolve failures")


class TestingAgent(BasePersonaAgent):
    """Persona that plans and interprets tests."""

    def build_input(self, context: Dict[str, Any]) -> str:
        coding: Dict[str, Any] = context.get("coding", {})
        return (
            "You are the Testing Agent. Generate pytest 8.4 compatible tests or smoke tests and the commands to run them. "
            "Recommend one retry strategy before rollback and document failure analysis steps."
            f"\n\nCoding Plan JSON:\n{coding}"
        )
