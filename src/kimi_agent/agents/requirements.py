from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

from ..orchestrator import Agent, AgentContext, AgentResult


@dataclass
class RequirementsArtifact:
    prompt: str
    document_excerpt: Optional[str]
    model_analysis: str
    acceptance_criteria: Dict[str, str]
    assumptions: Dict[str, str]

    def as_dict(self) -> Dict[str, object]:
        return {
            "prompt": self.prompt,
            "document_excerpt": self.document_excerpt,
            "model_analysis": self.model_analysis,
            "acceptance_criteria": self.acceptance_criteria,
            "assumptions": self.assumptions,
        }


class RequirementsAgent(Agent):
    name = "requirements"

    def execute(self, context: AgentContext) -> AgentResult:
        prompt = context.request.prompt or "No prompt supplied."
        doc_excerpt = _read_excerpt(context.request.input_docs)

        analysis_prompt = (
            "You are the Requirements Agent in a multi-agent coding pipeline. "
            "Summarise expectations, enumerate acceptance criteria, and list assumptions "
            "based on the developer prompt and optional input document excerpt.\n\n"
            f"Developer Prompt:\n{prompt}\n\n"
            f"Input Document Excerpt:\n{doc_excerpt or 'None provided.'}\n"
        )
        model_analysis = context.openai.generate_text(analysis_prompt)
        context.run_metadata["requirements.prompt"] = analysis_prompt
        context.run_metadata["requirements.model"] = getattr(context.openai, "model", "unknown")
        acceptance = _derive_criteria(prompt, doc_excerpt)
        assumptions = _derive_assumptions(prompt, doc_excerpt)

        artifact = RequirementsArtifact(
            prompt=prompt,
            document_excerpt=doc_excerpt,
            model_analysis=model_analysis,
            acceptance_criteria=acceptance,
            assumptions=assumptions,
        )

        context.run_metadata["requirements.summary"] = model_analysis
        context.run_metadata["requirements.acceptance"] = acceptance
        context.run_metadata["requirements.assumptions"] = assumptions
        context.run_metadata["requirements.document_excerpt"] = doc_excerpt

        details = {
            "prompt": prompt,
            "document_excerpt": doc_excerpt,
            "acceptance_criteria": acceptance,
            "assumptions": assumptions,
        }
        artifacts = {
            "requirements.json": {
                "type": "application/json",
                "payload": artifact.as_dict(),
            },
            "requirements.txt": {
                "type": "text/plain",
                "payload": model_analysis,
            },
        }

        return AgentResult(
            name=self.name,
            status="succeeded",
            summary="Requirements analysed and structured artifacts generated.",
            details=details,
            artifacts=artifacts,
        )


def _read_excerpt(path: Optional[Path], limit: int = 1200) -> Optional[str]:
    if not path:
        return None
    try:
        text = Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    if len(text) > limit:
        return text[:limit] + "..."
    return text


def _derive_criteria(prompt: str, doc_excerpt: Optional[str]) -> Dict[str, str]:
    hints = {}
    combined = " ".join(filter(None, [prompt, doc_excerpt or ""])).lower()
    if "next.js" in combined or "nextjs" in combined:
        hints["frontend"] = "Next.js 15 dashboard scaffold builds and runs locally."
        hints["auth"] = "Authentication stub wired with placeholder provider."
    if "fastapi" in combined:
        hints["api"] = "FastAPI CRUD endpoints implemented with Pydantic models."
    if "sqlite" in combined or "etl" in combined:
        hints["persistence"] = "Data pipeline ingests CSV into SQLite with idempotent runs."
    if "scikit" in combined or "ml" in combined:
        hints["ml"] = "Model trains deterministic baseline with metrics logged."
    if not hints:
        hints["baseline"] = "Generated project installs, runs smoke tests, and ships README."
    return hints


def _derive_assumptions(prompt: str, doc_excerpt: Optional[str]) -> Dict[str, str]:
    assumptions = {
        "environment": "Python 3.10+, Node 18+ available; local execution only.",
        "model": "Using gpt-5-mini via OpenAI Responses API.",
    }
    if "offline" in (prompt or "").lower():
        assumptions["network"] = "Assume offline run; rely on cached templates."
    if doc_excerpt and "license" in doc_excerpt.lower():
        assumptions["licensing"] = "Only MIT/Apache/BSD licensed dependencies permitted."
    return assumptions
