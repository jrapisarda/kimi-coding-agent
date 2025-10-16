"""Deterministic stand-in for the OpenAI Responses API."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class ContentTemplate:
    name: str
    body: str


class OpenAIClient:
    """A deliberately deterministic client that emulates content generation."""

    def __init__(self, templates_dir: Path) -> None:
        self.templates_dir = templates_dir
        self._templates = self._load_templates()

    def _load_templates(self) -> dict[str, ContentTemplate]:
        templates: dict[str, ContentTemplate] = {}
        for path in self.templates_dir.glob("*.txt"):
            templates[path.stem] = ContentTemplate(name=path.stem, body=path.read_text().strip())
        return templates

    def generate(self, brief: str, language: str = "en", tone: Optional[str] = None) -> str:
        base = self._templates.get("default")
        if not base:
            return f"[{language}] {brief}"
        tone_fragment = f" in a {tone} tone" if tone else ""
        return base.body.format(brief=brief, language=language, tone=tone_fragment)

    def translate(self, text: str, target_language: str) -> str:
        if target_language == "en":
            return text
        return f"[{target_language}] {text}"
