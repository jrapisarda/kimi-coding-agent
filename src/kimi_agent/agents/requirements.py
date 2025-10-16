"""Requirements agent definition."""

from __future__ import annotations

from typing import Any, Dict

from pydantic import Field

from .base import AgentOutput, BasePersonaAgent


class RequirementsOutput(AgentOutput):
    """Structured context describing requirements."""

    user_prompt: str = Field(..., description="Original user prompt")
    extracted_requirements: list[str] = Field(..., description="Bullet list of explicit requirements")
    constraints: list[str] = Field(default_factory=list, description="Constraints and assumptions")
    acceptance_criteria: list[str] = Field(default_factory=list, description="Acceptance criteria")
    risks: list[str] = Field(default_factory=list, description="Identified risks")


class RequirementsAgent(BasePersonaAgent):
    """Persona that distills requirements from prompts and docs."""

    def build_input(self, context: Dict[str, Any]) -> str:
        prompt = context.get("prompt", "")
        documents = context.get("documents", [])
        doc_descriptions = "\n\n".join(
            f"# Document: {doc['path']}\nType: {doc['media_type']}\n{doc['text']}" for doc in documents
        )
        return (
            "You are the Requirements Agent. Extract explicit requirements, constraints, acceptance criteria, and risks. "
            "Respect the latest framework versions mentioned in the docs."
            f"\n\nUser Prompt:\n{prompt}\n\nBackground Docs:\n{doc_descriptions}"
        )
