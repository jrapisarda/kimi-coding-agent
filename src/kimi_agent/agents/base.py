"""Base class for persona-specific agents."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type

from openai import OpenAI
from pydantic import BaseModel


class AgentOutput(BaseModel):
    """Base schema for agent outputs."""

    summary: str


class BasePersonaAgent(ABC):
    """Common wrapper around OpenAI Agents SDK personas."""

    def __init__(
        self,
        client: OpenAI,
        agent_id: Optional[str],
        model: str,
        instructions: Optional[str],
        output_model: Type[AgentOutput],
        name: str,
    ) -> None:
        self.client = client
        self.agent_id = agent_id
        self.model = model
        self.instructions = instructions
        self.output_model = output_model
        self.name = name

    @abstractmethod
    def build_input(self, context: Dict[str, Any]) -> str:
        """Return the input payload for the agent."""

    def run(self, context: Dict[str, Any]) -> AgentOutput:
        """Invoke the agent and parse the structured response."""

        input_payload = self.build_input(context)
        messages = []
        if self.agent_id is None and self.instructions:
            messages.append(
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": self.instructions,
                        }
                    ],
                }
            )
        messages.append(
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": input_payload,
                    }
                ],
            }
        )

        kwargs: Dict[str, Any] = {"input": messages}
        if self.agent_id is not None:
            kwargs["agent_id"] = self.agent_id
        else:
            kwargs["model"] = self.model

        responses = self.client.responses
        parse_fn = getattr(responses, "parse", None)

        if callable(parse_fn):
            try:
                response = parse_fn(response_format=self.output_model, **kwargs)
            except TypeError as exc:  # pragma: no cover - dependent on SDK version
                if "response_format" not in str(exc):
                    raise
                response = responses.create(**kwargs)
            else:
                parsed = self._coerce_output(response)
                if parsed is not None:
                    return parsed
                response = response  # fall through to generic parsing
        else:
            response = responses.create(**kwargs)

        fallback = self._coerce_output(response)
        if fallback is not None:
            return fallback

        if hasattr(response, "output_text") and response.output_text:
            raw = response.output_text
        else:
            raw = str(response)
        return self.output_model.model_validate_json(raw)

    def _coerce_output(self, response: Any) -> Optional[AgentOutput]:
        """Attempt to coerce SDK responses into the desired Pydantic model."""

        if isinstance(response, self.output_model):
            return response

        if hasattr(response, "output") and response.output:
            content = response.output[0]
            if hasattr(content, "content") and content.content:
                first_segment = content.content[0]
                if hasattr(first_segment, "text") and first_segment.text:
                    return self.output_model.model_validate_json(first_segment.text)
                if isinstance(first_segment, dict) and first_segment.get("text"):
                    return self.output_model.model_validate_json(first_segment["text"])
            if hasattr(content, "text") and content.text:
                return self.output_model.model_validate_json(content.text)

        return None
