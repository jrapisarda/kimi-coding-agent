"""Document ingestion utilities for Markdown and JSON sources."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

from rich.console import Console

console = Console()


@dataclass
class Document:
    """Container for input documents ingested by the pipeline."""

    path: Path
    text: str
    media_type: str

    def to_dict(self) -> dict:
        return {"path": str(self.path), "media_type": self.media_type, "text": self.text}


def read_document(path: Path) -> Document:
    """Read a Markdown or JSON document from disk."""

    if not path.exists():
        raise FileNotFoundError(f"Document not found: {path}")

    suffix = path.suffix.lower()
    if suffix not in {".md", ".markdown", ".json"}:
        raise ValueError(f"Unsupported document type: {path}")

    if suffix == ".json":
        payload = json.loads(path.read_text())
        text = json.dumps(payload, indent=2)
        media_type = "application/json"
    else:
        text = path.read_text()
        media_type = "text/markdown"

    return Document(path=path, text=text, media_type=media_type)


def load_documents(paths: Iterable[Path]) -> List[Document]:
    """Load multiple documents and log progress."""

    documents: List[Document] = []
    for path in paths:
        doc = read_document(path)
        console.log(f"Loaded document: {path} ({doc.media_type})")
        documents.append(doc)
    return documents
