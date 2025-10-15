"""Base agent class implementing common behaviour."""

from __future__ import annotations

import datetime as dt
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from tenacity import retry, stop_after_attempt, wait_exponential

from ..database import AgentRun, session_scope
from ..models import AgentContext
from ..services.openai_client import OpenAIClient
from ..utils.logging import get_logger


class BaseAgent(ABC):
    """Base class for all agents in the system."""

    system_prompt: str = "You are a helpful software engineering assistant."

    def __init__(self, name: str, client: OpenAIClient, session_factory) -> None:  # type: ignore[no-untyped-def]
        self.name = name
        self._client = client
        self._session_factory = session_factory
        self._logger = get_logger(name)

    def run(self, context: AgentContext) -> Dict[str, Any]:
        """Execute the agent with retry logic and persistence."""

        self._logger.info("Starting agent execution", extra={"agent": self.name})
        agent_run_id = self._create_agent_run(context)
        try:
            output = self._execute_with_retry(context)
            self._complete_agent_run(agent_run_id, status="completed", context=output)
            self._logger.info("Agent completed", extra={"agent": self.name})
            return output
        except Exception as exc:  # noqa: BLE001
            self._logger.exception("Agent failed", extra={"agent": self.name})
            self._complete_agent_run(agent_run_id, status="failed", error=str(exc))
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def _execute_with_retry(self, context: AgentContext) -> Dict[str, Any]:
        return self.execute(context)

    @abstractmethod
    def execute(self, context: AgentContext) -> Dict[str, Any]:
        """Subclasses implement the agent logic."""

    def create_llm_response(self, prompt: str, *, system_prompt: Optional[str] = None) -> str:
        response = self._client.create_response(prompt, system_prompt=system_prompt or self.system_prompt)
        text = getattr(response, "output_text", None)
        if text:
            return str(text)
        # Fallback for structured responses
        output = getattr(response, "output", None)
        if isinstance(output, list) and output:
            message = output[0]
            content = getattr(message, "content", None)
            if isinstance(content, list) and content:
                text_item = content[0]
                maybe_text = getattr(text_item, "text", None)
                if maybe_text:
                    return str(getattr(maybe_text, "value", maybe_text))
        return ""

    def _create_agent_run(self, context: AgentContext) -> int:
        with session_scope(self._session_factory) as session:
            agent_run = AgentRun(
                agent_name=self.name,
                status="running",
                context=context.model_dump(mode="json"),
            )
            session.add(agent_run)
            session.flush()
            return agent_run.id

    def _complete_agent_run(self, agent_run_id: int, *, status: str, context: Optional[Dict[str, Any]] = None, error: Optional[str] = None) -> None:
        with session_scope(self._session_factory) as session:
            run = session.get(AgentRun, agent_run_id)
            if not run:
                return
            run.status = status
            run.completed_at = dt.datetime.utcnow()
            if context is not None:
                run.context = context
            if error:
                run.error_message = error


__all__ = ["BaseAgent"]
