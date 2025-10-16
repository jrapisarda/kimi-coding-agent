"""Coding agent definition."""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional

from pydantic import Field, ValidationError

from .base import AgentOutput, BasePersonaAgent


class CodingOutput(AgentOutput):
    """Structured plan for code generation."""

    tasks: list[str] = Field(default_factory=list, description="Ordered list of coding tasks")
    commands: list[str] = Field(default_factory=list, description="Shell commands to execute")
    files: dict[str, str] = Field(default_factory=dict, description="Mapping of file paths to proposed contents")
    dependencies: list[str] = Field(default_factory=list, description="Dependencies to add")


class CodingAgent(BasePersonaAgent):
    """Persona that plans code changes and tool invocations."""

    _SECTION_ALIASES = {
        "tasks": {"implementation plan", "plan", "tasks", "steps", "todo"},
        "commands": {"commands", "shell commands", "terminal commands", "cli"},
        "files": {"files", "file diffs", "proposed file diffs", "diffs", "patches"},
        "dependencies": {"dependencies", "deps", "requirements"},
        "summary": {"summary", "overview"},
    }

    _LIST_ITEM_RE = re.compile(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)(?P<text>.+?)\s*$")
    _FILE_LINE_RE = re.compile(
        r"^\s*(?:[-*+]|\d+[.)])?\s*(?P<path>(?:\.{0,2}/)?[\w.\-/\\]+)\s*:?$"
    )

    def build_input(self, context: Dict[str, Any]) -> str:
        requirements: Dict[str, Any] = context.get("requirements", {})
        return (
            "You are the Coding Agent. Produce a concise implementation plan, explicit shell commands, and proposed file diffs."
            "Use deterministic seeds and prefer local execution."
            f"\n\nRequirements JSON:\n{requirements}"
        )

    def parse_fallback(self, raw: str, context: Dict[str, Any]) -> CodingOutput:  # noqa: ARG002
        """Parse free-form text responses from the coding agent."""

        try:
            return super().parse_fallback(raw, context)  # type: ignore[return-value]
        except ValidationError:
            pass

        lines = [line.rstrip("\n") for line in raw.splitlines()]
        sections = self._split_into_sections(lines)

        summary = self._extract_summary(sections, lines)
        tasks = self._extract_list(sections.get("tasks"))
        if not tasks:
            tasks = self._extract_list(lines)

        commands = self._extract_commands(sections.get("commands"))
        dependencies = self._extract_dependencies(sections.get("dependencies"))
        files = self._extract_files(sections.get("files"))

        return CodingOutput(
            summary=summary,
            tasks=tasks,
            commands=commands,
            files=files,
            dependencies=dependencies,
        )

    def _normalize_heading(self, text: str) -> str:
        normalized = re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()
        return normalized

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
        return "Coding agent response"

    def _extract_list(self, lines: Optional[Iterable[str]]) -> List[str]:
        items: List[str] = []
        if not lines:
            return items
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
                        commands.append("\n".join(block).strip())
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
                commands.append(match.group("text").strip())
                continue
            if stripped.startswith("$"):
                commands.append(stripped.lstrip("$").strip())
        if collecting_block and block:
            commands.append("\n".join(block).strip())
        return commands

    def _extract_dependencies(self, lines: Optional[Iterable[str]]) -> List[str]:
        if not lines:
            return []
        deps: List[str] = []
        for line in lines:
            match = self._LIST_ITEM_RE.match(line)
            if match:
                deps.append(match.group("text").strip())
        return deps

    def _extract_files(self, lines: Optional[Iterable[str]]) -> Dict[str, str]:
        if not lines:
            return {}

        files: Dict[str, str] = {}
        current_path: Optional[str] = None
        collecting_block = False
        block: List[str] = []

        for raw_line in lines:
            line = raw_line.rstrip("\n")
            stripped = line.strip()
            if stripped.startswith("```"):
                if collecting_block:
                    collecting_block = False
                    if current_path and block:
                        files[current_path] = "\n".join(block).strip()
                    block = []
                    current_path = None
                else:
                    collecting_block = True
                    block = []
                continue
            if collecting_block:
                block.append(line)
                continue

            match = self._FILE_LINE_RE.match(stripped)
            if match:
                path = match.group("path").strip().rstrip(":")
                path = path.lstrip("-*").strip()
                current_path = path if path else None
                continue

        if collecting_block and block and current_path:
            files[current_path] = "\n".join(block).strip()

        return files
