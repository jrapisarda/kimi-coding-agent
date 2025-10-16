"""Documentation agent definition."""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional

from pydantic import Field, ValidationError

from .base import AgentOutput, BasePersonaAgent


class DocumentationOutput(AgentOutput):
    """Structured README draft and changelog."""

    quickstart: str = Field(..., description="Quickstart instructions")
    commands: list[str] = Field(default_factory=list, description="Important commands to surface")
    limitations: list[str] = Field(default_factory=list, description="Known limitations")


class DocumentationAgent(BasePersonaAgent):
    """Persona that generates documentation."""

    _SECTION_ALIASES = {
        "summary": {"summary", "overview"},
        "quickstart": {
            "quickstart",
            "getting started",
            "setup",
            "installation",
            "install",
            "usage",
            "how to run",
        },
        "commands": {"commands", "command cheat sheet", "cli"},
        "limitations": {"limitations", "known issues", "caveats", "constraints", "notes"},
    }

    _LIST_ITEM_RE = re.compile(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)(?P<text>.+?)\s*$")

    def build_input(self, context: Dict[str, Any]) -> str:
        summary = context.get("summary", "")
        testing = context.get("testing", {})
        return (
            "You are the Documentation Agent. Produce a README section with quickstart steps, key commands, reproducibility notes, and known limitations."
            f"\n\nRun Summary:\n{summary}\n\nTesting JSON:\n{testing}"
        )

    def parse_fallback(self, raw: str, context: Dict[str, Any]) -> DocumentationOutput:  # noqa: ARG002
        """Parse free-form text responses from the documentation agent."""

        try:
            return super().parse_fallback(raw, context)  # type: ignore[return-value]
        except ValidationError:
            pass

        lines = [line.rstrip("\n") for line in raw.splitlines()]
        sections = self._split_into_sections(lines)

        summary = self._extract_summary(sections, lines)
        quickstart = self._extract_quickstart(sections.get("quickstart"), summary)
        commands = self._extract_commands(sections.get("commands"))
        limitations = self._extract_list(sections.get("limitations"))

        if not commands:
            commands = self._extract_commands(lines)
        if not limitations:
            limitations = self._extract_list(lines)
        if not quickstart:
            quickstart = summary or "Refer to the coding plan for setup instructions."

        return DocumentationOutput(
            summary=summary,
            quickstart=quickstart,
            commands=commands,
            limitations=limitations,
        )

    def _normalize_heading(self, text: str) -> str:
        return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()

    def _split_into_sections(self, lines: List[str]) -> Dict[str, List[str]]:
        sections: Dict[str, List[str]] = {key: [] for key in self._SECTION_ALIASES}
        current: Optional[str] = None
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            normalized = self._normalize_heading(stripped.rstrip(":"))
            matched = False
            for section, aliases in self._SECTION_ALIASES.items():
                if normalized in aliases or any(
                    normalized.startswith(f"{alias} ") for alias in aliases
                ):
                    current = section
                    matched = True
                    break
            if matched:
                continue
            if current and current in sections:
                sections[current].append(line)
        return sections

    def _extract_summary(self, sections: Dict[str, List[str]], lines: List[str]) -> str:
        summary_lines = sections.get("summary") or []
        for line in summary_lines:
            cleaned = line.strip()
            if cleaned:
                return cleaned

        section_aliases = {
            alias
            for aliases in self._SECTION_ALIASES.values()
            for alias in aliases
        }
        for line in lines:
            cleaned = line.strip()
            if not cleaned:
                continue
            normalized = self._normalize_heading(cleaned.rstrip(":"))
            if normalized in section_aliases:
                continue
            if self._LIST_ITEM_RE.match(cleaned):
                continue
            return cleaned[:300]
        return "Documentation agent response"

    def _extract_quickstart(
        self, lines: Optional[Iterable[str]], summary: str
    ) -> str:
        if not lines:
            return summary

        parts: List[str] = []
        collecting_block = False
        block: List[str] = []
        for raw_line in lines:
            line = raw_line.rstrip()
            stripped = line.strip()
            if stripped.startswith("```"):
                if collecting_block:
                    collecting_block = False
                    if block:
                        parts.append("\n".join(block).strip())
                    block = []
                else:
                    collecting_block = True
                    block = []
                continue
            if collecting_block:
                block.append(line)
                continue
            match = self._LIST_ITEM_RE.match(stripped)
            if match:
                parts.append(f"- {match.group('text').strip()}")
                continue
            if stripped:
                parts.append(stripped)

        if collecting_block and block:
            parts.append("\n".join(block).strip())

        quickstart_text = "\n".join(parts).strip()
        return quickstart_text or summary

    def _extract_list(self, lines: Optional[Iterable[str]]) -> List[str]:
        if not lines:
            return []
        items: List[str] = []
        for line in lines:
            match = self._LIST_ITEM_RE.match(line)
            if match:
                items.append(match.group("text").strip())
        return items

    def _extract_commands(self, lines: Optional[Iterable[str]]) -> List[str]:
        if not lines:
            return []

        commands: List[str] = []
        collecting_block = False
        block: List[str] = []
        for raw_line in lines:
            line = raw_line.rstrip()
            stripped = line.strip()
            if stripped.startswith("```"):
                if collecting_block:
                    collecting_block = False
                    if block:
                        block_text = "\n".join(block).strip()
                        if self._looks_like_command(block_text):
                            commands.append(block_text)
                    block = []
                else:
                    collecting_block = True
                    block = []
                continue
            if collecting_block:
                block.append(line)
                continue
            match = self._LIST_ITEM_RE.match(stripped)
            if match:
                candidate = match.group("text").strip()
                if self._looks_like_command(candidate):
                    commands.append(candidate)
                continue
            if stripped.startswith("$"):
                command_text = stripped.lstrip("$").strip()
                if self._looks_like_command(command_text):
                    commands.append(command_text)

        if collecting_block and block:
            block_text = "\n".join(block).strip()
            if self._looks_like_command(block_text):
                commands.append(block_text)

        return commands

    def _looks_like_command(self, text: str) -> bool:
        if not text:
            return False
        first_line = text.splitlines()[0].strip()
        if not first_line:
            return False
        token = first_line.split()[0].lower()
        if token.startswith("./") or token.startswith("../"):
            return True
        command_prefixes = (
            "python",
            "pip",
            "pytest",
            "uv",
            "poetry",
            "nox",
            "tox",
            "make",
            "bash",
            "sh",
            "docker",
            "reqs_agent",
        )
        if token in {"run", "invoke"} and len(first_line.split()) > 1:
            return True
        return token.startswith(command_prefixes)
