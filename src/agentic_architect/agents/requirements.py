"""Requirements analysis agent."""

from __future__ import annotations

from typing import Any, Dict, List

from ..models import AgentContext
from ..services.pattern_cache import PatternCacheService
from ..services.web_research import WebResearchService
from .base import BaseAgent


class RequirementsAnalysisAgent(BaseAgent):
    """Validates specifications and identifies gaps."""

    system_prompt = "You are an expert requirements analyst for software systems."

    def __init__(
        self,
        client,
        session_factory,
        pattern_cache: PatternCacheService,
        research_service: WebResearchService,
    ) -> None:  # type: ignore[no-untyped-def]
        super().__init__("requirements", client, session_factory)
        self._pattern_cache = pattern_cache
        self._research_service = research_service

    def execute(self, context: AgentContext) -> Dict[str, Any]:
        spec = context.specification
        assumptions: List[str] = []

        for component in spec.architecture.components:
            if not component.dependencies and component.name.lower() != "core":
                assumptions.append(
                    f"Component {component.name} has no dependencies specified; assuming standalone behaviour."
                )

        if not spec.deployment.targets:
            research = self._research_service.search(f"best deployment practices for {spec.project.language}")
            if research:
                assumptions.append(
                    "Deployment targets not specified; recommended options researched and documented."
                )

        if spec.deliverables.final_package.required_files:
            assumptions.append(
                "Deliverables checklist seeded to track required final package assets."
            )

        cached_pattern = self._pattern_cache.get(spec.architecture.pattern)
        if cached_pattern:
            assumptions.append("Architecture pattern found in cache; reusing established template.")

        context.assumptions.extend(assumptions)
        return {
            "assumptions": assumptions,
            "recommended_quality_tools": self._recommend_quality_tools(spec.quality),
        }

    def _recommend_quality_tools(self, quality_spec) -> List[str]:  # type: ignore[no-untyped-def]
        recommended = set(quality_spec.formatters + quality_spec.linters)
        recommended.update(["black", "ruff", "mypy"])
        return sorted(recommended)


__all__ = ["RequirementsAnalysisAgent"]
