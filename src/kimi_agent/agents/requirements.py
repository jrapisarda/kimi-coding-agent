"""Requirements agent definition."""

from __future__ import annotations

from typing import Any, Dict, List

from pydantic import Field, ValidationError

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

    def parse_fallback(self, raw: str, context: Dict[str, Any]) -> RequirementsOutput:
        # Attempt strict JSON parsing first.
        try:
            return super().parse_fallback(raw, context)  # type: ignore[misc]
        except ValidationError:
            pass

        aliases = {
            "summary": {"summary", "scope", "overview"},
            "extracted_requirements": {"requirements", "requirement", "requested work"},
            "constraints": {"constraints", "assumptions", "limitations"},
            "acceptance_criteria": {"acceptance criteria", "definition of done", "success criteria"},
            "risks": {"risks", "concerns", "open questions"},
        }

        summary_lines: List[str] = []
        buckets: Dict[str, List[str]] = {
            "extracted_requirements": [],
            "constraints": [],
            "acceptance_criteria": [],
            "risks": [],
        }

        current_section: str | None = None

        def normalize_heading(line: str) -> tuple[str | None, str]:
            for field, names in aliases.items():
                for name in names:
                    prefix = f"{name}:"
                    if line.lower().startswith(prefix):
                        remainder = line[len(prefix) :].strip()
                        return field, remainder
                    if line.lower().startswith(name) and line.endswith(":"):
                        return field, ""
            return None, line

        def sanitize_item(text: str) -> str:
            stripped = text.lstrip("-*•0123456789.) ").strip()
            return stripped

        for raw_line in raw.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            heading_field, remainder = normalize_heading(line)
            if heading_field:
                current_section = heading_field
                if heading_field == "summary":
                    if remainder:
                        summary_lines.append(remainder)
                elif remainder:
                    buckets[heading_field].append(sanitize_item(remainder))
                continue

            if line[0] in "-*•" or line[:2].isdigit():
                cleaned = sanitize_item(line)
                if current_section and current_section in buckets:
                    if cleaned:
                        buckets[current_section].append(cleaned)
                else:
                    summary_lines.append(cleaned)
                continue

            if current_section and current_section in buckets:
                cleaned = sanitize_item(line)
                if cleaned:
                    buckets[current_section].append(cleaned)
            else:
                summary_lines.append(line)

        summary = " ".join(summary_lines).strip()
        if not summary:
            remaining_lines = [line.strip() for line in raw.splitlines() if line.strip()]
            if remaining_lines:
                summary = remaining_lines[0]
            else:
                summary = raw.strip()
        user_prompt = context.get("prompt", "")

        return RequirementsOutput(
            summary=summary,
            user_prompt=user_prompt,
            extracted_requirements=buckets["extracted_requirements"],
            constraints=buckets["constraints"],
            acceptance_criteria=buckets["acceptance_criteria"],
            risks=buckets["risks"],
        )
