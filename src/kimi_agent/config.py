"""Configuration models for the Kimi coding agent."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

DEFAULT_MODEL = "gpt-5.0"


@dataclass
class AgentConfig:
    """Configuration for a single agent persona."""

    name: str
    system_prompt: str
    model: str = DEFAULT_MODEL
    instructions: Optional[str] = None
    tools: Optional[List[str]] = None


@dataclass
class RunConfig:
    """Configuration for orchestrating a full run."""

    target_path: Path
    prompt: str
    input_documents: List[Path] = field(default_factory=list)
    enable_web_search: bool = False
    enable_file_search: bool = False
    enable_code_interpreter: bool = True
    metadata: Dict[str, str] = field(default_factory=dict)
    workspace_name: Optional[str] = None

    def resolved(self) -> "RunConfig":
        self.target_path = self.target_path.expanduser().resolve()
        self.input_documents = [path.expanduser().resolve() for path in self.input_documents]
        return self
