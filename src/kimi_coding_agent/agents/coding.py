"""Coding agent implementation."""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

from ..schemas import CodingContext, RequirementsContext, RunConfig
from .base import BaseAgent

logger = logging.getLogger(__name__)


class CodingAgent(BaseAgent):
    """Turns structured requirements into an actionable implementation plan."""

    def __init__(self) -> None:
        super().__init__(name="coding")

    def run(self, *, config: RunConfig, shared_state: Dict[str, Any]) -> Dict[str, Any]:
        req_context = RequirementsContext.model_validate(shared_state.get("requirements", {}))
        plan = _build_plan(req_context)
        dependency_notes = _dependency_hints(req_context)

        target_dir = config.target_path
        target_dir.mkdir(parents=True, exist_ok=True)
        plan_file = target_dir / "agent_plan.json"
        plan_file.write_text(
            json.dumps(
                {
                    "plan": plan,
                    "dependency_notes": dependency_notes,
                    "requirements": req_context.model_dump(),
                },
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )

        summary = "Prepared implementation plan with dependency guidance."
        context = CodingContext(
            plan=plan,
            generated_files=[plan_file],
            dependency_notes=dependency_notes,
            summary=summary,
        )
        context_payload = context.model_dump()
        context_payload["summary"] = summary
        shared_state[self.name] = context_payload
        return context_payload


def _build_plan(requirements: RequirementsContext) -> List[str]:
    plan: List[str] = []
    if not requirements.structured_requirements:
        plan.append("Review requirements and prepare scaffolding for baseline stacks.")
    for idx, item in enumerate(requirements.structured_requirements, start=1):
        plan.append(f"Implement requirement {idx}: {item}")
    if requirements.assumptions:
        plan.append("Validate assumptions with user and adjust plan if needed.")
    plan.append("Record generated files and persist run metadata to SQLite.")
    return plan


def _dependency_hints(requirements: RequirementsContext) -> List[str]:
    hints: List[str] = []
    text_blob = " ".join(requirements.structured_requirements).lower()
    if "next.js" in text_blob or "nextjs" in text_blob:
        hints.append("Ensure Node.js >= 18.18 and align with Next.js 15 scaffolding.")
    if "fastapi" in text_blob:
        hints.append("Use FastAPI >= 0.118 with uvicorn and pytest 8.4+ for testing.")
    if "pandas" in text_blob or "etl" in text_blob:
        hints.append("Pin pandas >= 2.3 and leverage pyarrow for performant IO when available.")
    if "scikit" in text_blob:
        hints.append("Adopt scikit-learn >= 1.7 with deterministic random_state usage.")
    if not hints:
        hints.append("Capture environment versions and dependency pins for reproducibility.")
    return hints
