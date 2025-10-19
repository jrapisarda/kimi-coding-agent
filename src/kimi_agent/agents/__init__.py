from typing import Iterable

from ..orchestrator import Agent
from .coding import CodingAgent
from .documentation import DocumentationAgent
from .requirements import RequirementsAgent
from .testing import TestingAgent


def build_pipeline_agents() -> Iterable[Agent]:
    """Factory returning the ordered agents for the sprint-two pipeline."""
    return [
        RequirementsAgent(),
        CodingAgent(),
        TestingAgent(),
        DocumentationAgent(),
    ]


__all__ = ["build_pipeline_agents"]
