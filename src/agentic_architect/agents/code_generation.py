"""Code generation agent that scaffolds the project."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from ..models import AgentContext
from ..services.pattern_cache import PatternCacheService
from .base import BaseAgent

try:  # Optional import for bundled example assets
    from ..examples.bioinformatics_etl_assets import BIOINFORMATICS_ETL_FILES
except ImportError:  # pragma: no cover - fallback when assets are unavailable
    BIOINFORMATICS_ETL_FILES = {}


class CodeGenerationAgent(BaseAgent):
    """Generates project scaffolding using cached patterns and LLM outputs."""

    system_prompt = "You are a principal software engineer generating production ready codebases."

    def __init__(self, client, session_factory, pattern_cache: PatternCacheService) -> None:  # type: ignore[no-untyped-def]
        super().__init__("code-generation", client, session_factory)
        self._pattern_cache = pattern_cache

    def execute(self, context: AgentContext) -> Dict[str, Any]:
        spec = context.specification
        project_root = context.workspace_root / spec.project.name.replace(" ", "-")
        project_root.mkdir(parents=True, exist_ok=True)
        context.generated_paths.append(project_root)

        pattern_key = spec.architecture.pattern
        if spec.project.name == "bioinformatics-etl-cli" and BIOINFORMATICS_ETL_FILES:
            self._generate_bioinformatics_project(project_root)
        else:
            cached_template = self._pattern_cache.get(pattern_key)
            if cached_template:
                self._write_cached_template(project_root, cached_template)
            else:
                prompt = self._build_prompt(spec)
                response = self.create_llm_response(prompt)
                self._write_plan(project_root, response)
                self._pattern_cache.set(pattern_key, response)

        return {"project_root": str(project_root)}

    def _build_prompt(self, spec) -> str:  # type: ignore[no-untyped-def]
        return (
            "Generate a high level scaffold for the following project specification in JSON.\n"
            "Include recommended directories, core modules, configuration, and tests.\n"
            f"JSON:\n{spec.model_dump_json(indent=2)}"
        )

    def _write_plan(self, project_root: Path, plan_text: str) -> None:
        plan_path = project_root / "ScaffoldPlan.md"
        plan_path.write_text(plan_text, encoding="utf-8")

    def _write_cached_template(self, project_root: Path, template: str) -> None:
        template_path = project_root / "CachedTemplate.md"
        template_path.write_text(template, encoding="utf-8")

    def _generate_bioinformatics_project(self, project_root: Path) -> None:
        """Materialize the bundled bioinformatics ETL CLI example project."""

        for relative_path, content in BIOINFORMATICS_ETL_FILES.items():
            target = project_root / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            if content:
                target.write_text(content, encoding="utf-8")
            else:
                target.touch()


__all__ = ["CodeGenerationAgent"]
