"""Agent orchestration pipeline."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

import typer

from ..agents.base import BaseAgent
from ..agents.code_generation import CodeGenerationAgent
from ..agents.documentation import DocumentationAgent
from ..agents.quality import QualityAssuranceAgent
from ..agents.requirements import RequirementsAnalysisAgent
from ..agents.testing import TestingAgent
from ..agents.version_control import VersionControlAgent
from ..config import Settings
from ..database import create_session_factory
from ..models import AgentContext, ProjectSpecification
from ..services.openai_client import OpenAIClient
from ..services.pattern_cache import PatternCacheService
from ..services.web_research import WebResearchService
from ..utils.logging import configure_logging, get_logger


class AgentOrchestrator:
    """Coordinates execution of all agents for a project specification."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings()
        configure_logging()
        self._logger = get_logger("AgentOrchestrator")
        self._session_factory = create_session_factory(
            self.settings.database.url, echo=self.settings.database.echo
        )
        self._client = OpenAIClient(self.settings.openai)
        self._pattern_cache = PatternCacheService(self._session_factory)
        self._research = WebResearchService(self.settings.research, self._session_factory)
        self._agents = self._create_agents()

    def _create_agents(self) -> List[BaseAgent]:
        return [
            RequirementsAnalysisAgent(
                client=self._client,
                session_factory=self._session_factory,
                pattern_cache=self._pattern_cache,
                research_service=self._research,
            ),
            CodeGenerationAgent(self._client, self._session_factory, self._pattern_cache),
            TestingAgent(self._client, self._session_factory),
            DocumentationAgent(self._client, self._session_factory),
            QualityAssuranceAgent(self._client, self._session_factory),
            VersionControlAgent(self._client, self._session_factory),
        ]

    def run(self, spec: ProjectSpecification) -> Dict[str, Dict[str, str]]:
        context = AgentContext(specification=spec, workspace_root=self.settings.workspace_root)
        results: Dict[str, Dict[str, str]] = {}

        for agent in self._agents:
            self._logger.info("Running agent %s", agent.name)
            result = agent.run(context)
            results[agent.name] = {k: str(v) for k, v in result.items()}

        return results


app = typer.Typer(help="Multi-agent JSON to code generator")


@app.command()
def generate(spec_path: Path, workspace: Path = typer.Option(Path.cwd(), "--workspace")) -> None:
    """Generate a project from a JSON specification file."""

    settings = Settings(workspace_root=workspace)
    orchestrator = AgentOrchestrator(settings)
    data = json.loads(spec_path.read_text(encoding="utf-8"))
    spec = ProjectSpecification.from_json(data)
    orchestrator.run(spec)
    typer.echo("Generation complete")


__all__ = ["AgentOrchestrator", "app"]
