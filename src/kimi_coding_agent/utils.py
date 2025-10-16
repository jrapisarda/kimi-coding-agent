"""Utility helpers for the agent pipeline."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Iterable, List

from .schemas import InputDocument

logger = logging.getLogger(__name__)


def discover_input_documents(path: Path) -> List[InputDocument]:
    """Load Markdown/JSON documents from a file or directory."""

    if not path.exists():
        raise FileNotFoundError(f"Input docs path {path} does not exist")

    if path.is_file():
        return [_load_document(path)]

    documents: List[InputDocument] = []
    for entry in sorted(_iter_docs(path)):
        documents.append(_load_document(entry))
    return documents


def _iter_docs(directory: Path) -> Iterable[Path]:
    for entry in directory.iterdir():
        if entry.is_dir():
            yield from _iter_docs(entry)
            continue
        if entry.suffix.lower() in {".md", ".markdown", ".json", ".txt"}:
            yield entry


def _load_document(path: Path) -> InputDocument:
    content = path.read_text(encoding="utf-8")
    content_type = "json" if path.suffix.lower() == ".json" else "markdown"
    if content_type == "json":
        try:
            json.loads(content)
        except json.JSONDecodeError:
            logger.warning("JSON document %s is not valid JSON; treating as text", path)
            content_type = "text"
    return InputDocument(source_path=path, content=content, content_type=content_type)
