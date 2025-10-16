"""Testing agent definition."""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional

from pydantic import Field, ValidationError

from .base import AgentOutput, BasePersonaAgent


class TestingOutput(AgentOutput):
    """Structured test instructions."""

    tests: list[str] = Field(default_factory=list, description="Test cases to generate")
    commands: list[str] = Field(default_factory=list, description="Commands to run tests")
    remediation: list[str] = Field(default_factory=list, description="Steps to resolve failures")


class TestingAgent(BasePersonaAgent):
    """Persona that plans and interprets tests."""

    _SECTION_ALIASES = {
        "summary": {"summary", "overview"},
        "tests": {"tests", "test plan", "pytest", "smoke tests"},
        "commands": {"commands", "shell", "execution", "run"},
        "remediation": {"remediation", "recovery", "failure analysis", "rollback"},
    }

    _LIST_ITEM_RE = re.compile(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)(?P<text>.+?)\s*$")

    def build_input(self, context: Dict[str, Any]) -> str:
        coding: Dict[str, Any] = context.get("coding", {})
        return (
            "You are the Testing Agent. Generate pytest 8.4 compatible tests or smoke tests and the commands to run them. "
            "Recommend one retry strategy before rollback and document failure analysis steps."
            f"\n\nCoding Plan JSON:\n{coding}"
        )

    def parse_fallback(self, raw: str, context: Dict[str, Any]) -> TestingOutput:  # noqa: ARG002
        """Parse free-form text responses from the testing agent."""

        try:
            return super().parse_fallback(raw, context)  # type: ignore[return-value]
        except ValidationError:
            pass

        lines = [line.rstrip("\n") for line in raw.splitlines()]
        sections = self._split_into_sections(lines)

        summary = self._extract_summary(sections, lines)
        tests = self._extract_list(sections.get("tests"))
        commands = self._extract_commands(sections.get("commands"), allow_relaxed=True)
        remediation = self._extract_list(sections.get("remediation"))

        if not tests:
            tests = self._extract_list(lines)
        if not commands:
            commands = self._extract_commands(lines)
        if not remediation:
            remediation = self._extract_list(lines)

        return TestingOutput(
            summary=summary,
            tests=tests,
            commands=commands,
            remediation=remediation,
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
        return "Testing agent response"

    def _extract_list(self, lines: Optional[Iterable[str]]) -> List[str]:
        if not lines:
            return []
        items: List[str] = []
        for line in lines:
            match = self._LIST_ITEM_RE.match(line)
            if match:
                items.append(match.group("text").strip())
        return items

    def _extract_commands(
        self, lines: Optional[Iterable[str]], *, allow_relaxed: bool = False
    ) -> List[str]:
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
                        if allow_relaxed or self._looks_like_command(block_text):
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
                if allow_relaxed or self._looks_like_command(candidate):
                    commands.append(candidate)
                continue
            if stripped.startswith("$"):
                command_text = stripped.lstrip("$").strip()
                if allow_relaxed or self._looks_like_command(command_text):
                    commands.append(command_text)

        if collecting_block and block:
            block_text = "\n".join(block).strip()
            if allow_relaxed or self._looks_like_command(block_text):
                commands.append(block_text)

        return commands

    def _looks_like_command(self, text: str) -> bool:
        if not text:
            return False
        first_line = text.splitlines()[0].strip()
        if not first_line:
            return False
        token = first_line.split()[0].lower()
        command_prefixes = (
            "pytest",
            "python",
            "pip",
            "poetry",
            "nox",
            "tox",
            "uv",
            "make",
            "coverage",
            "bash",
            "sh",
            "docker",
        )
        if token.startswith("./") or token.startswith("../"):
            return True
        if token in {"run", "invoke"} and len(first_line.split()) > 1:
            return True
        return token.startswith(command_prefixes)
