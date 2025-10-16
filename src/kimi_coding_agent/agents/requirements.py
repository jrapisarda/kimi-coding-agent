"""Requirements agent implementation."""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List

from ..schemas import InputDocument, RequirementsContext, RunConfig
from ..utils import discover_input_documents
from .base import BaseAgent

logger = logging.getLogger(__name__)


class RequirementsAgent(BaseAgent):
    """Parses raw prompts and documents into a structured context."""

    def __init__(self) -> None:
        super().__init__(name="requirements")

    def run(self, *, config: RunConfig, shared_state: Dict[str, Any]) -> Dict[str, Any]:
        documents = []
        if config.input_docs is not None:
            documents = discover_input_documents(config.input_docs)
        summary = _summarize_requirements(config.prompt, documents)
        structured = _extract_requirements(documents)
        assumptions = _extract_assumptions(documents, config.prompt)

        context = RequirementsContext(
            summary=summary,
            structured_requirements=structured,
            assumptions=assumptions,
            documents=documents,
            raw_prompt=config.prompt,
        )
        shared_state[self.name] = context.model_dump()
        return context.model_dump()


def _summarize_requirements(prompt: str | None, documents: List[InputDocument]) -> str:
    snippets: List[str] = []
    if prompt:
        snippets.append(prompt.strip().splitlines()[0])
    for doc in documents:
        first_line = doc.content.strip().splitlines()[0] if doc.content.strip() else ""
        if first_line:
            snippets.append(first_line)
    joined = " ".join(snippets)
    return joined[:500] if joined else "No explicit requirements provided."


def _extract_requirements(documents: List[InputDocument]) -> List[str]:
    requirements: List[str] = []
    for doc in documents:
        if doc.content_type == "json":
            try:
                payload = json.loads(doc.content)
            except json.JSONDecodeError:
                logger.debug("Skipping invalid JSON document: %s", doc.source_path)
                continue
            requirements.extend(_collect_from_json(payload))
        else:
            requirements.extend(_collect_from_text(doc.content))
    deduped = list(dict.fromkeys([req.strip() for req in requirements if req.strip()]))
    return deduped


def _collect_from_json(data: Any) -> List[str]:
    if isinstance(data, str):
        return [data]
    if isinstance(data, list):
        results: List[str] = []
        for item in data:
            results.extend(_collect_from_json(item))
        return results
    if isinstance(data, dict):
        results: List[str] = []
        for key, value in data.items():
            if key.lower() in {"requirements", "goals", "tasks", "must", "should"}:
                results.extend(_collect_from_json(value))
            elif isinstance(value, (dict, list)):
                results.extend(_collect_from_json(value))
        return results
    return []


def _collect_from_text(content: str) -> List[str]:
    bullet_pattern = re.compile(r"^(?:[-*]|\d+[.)])\s+(.*)")
    requirements: List[str] = []
    for line in content.splitlines():
        match = bullet_pattern.match(line.strip())
        if match:
            requirements.append(match.group(1))
    return requirements


def _extract_assumptions(documents: List[InputDocument], prompt: str | None) -> List[str]:
    assumptions: List[str] = []
    for doc in documents:
        if "assumption" in doc.content.lower():
            for line in doc.content.splitlines():
                if "assumption" in line.lower():
                    assumptions.append(line.strip())
    if prompt and "assume" in prompt.lower():
        assumptions.append(prompt)
    deduped = list(dict.fromkeys(assumptions))
    return deduped
