"""Abstract base class for pipeline agents."""
from __future__ import annotations

import abc
from datetime import datetime, timezone
from typing import Any, Dict

from ..schemas import RunConfig


class BaseAgent(abc.ABC):
    """Defines the contract implemented by all agents."""

    name: str

    def __init__(self, name: str) -> None:
        self.name = name

    @abc.abstractmethod
    def run(self, *, config: RunConfig, shared_state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the agent and return a serializable payload."""

    def now(self) -> datetime:
        """Return a timezone-naive timestamp for persistence."""

        return datetime.now(timezone.utc)
