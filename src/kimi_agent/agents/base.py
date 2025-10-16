"""Base class for persona-specific agents."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any, Dict, Type

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
        agent_id: str,
        output_model: Type[AgentOutput],
        name: str,
    ) -> None:
        self.client = client
        self.agent_id = agent_id
        self.output_model = output_model
        self.name = name

    @abstractmethod
    def build_input(self, context: Dict[str, Any]) -> str:
        """Return the input payload for the agent."""

    def run(self, context: Dict[str, Any]) -> AgentOutput:
        """Invoke the agent and parse the structured response."""

        input_payload = self.build_input(context)
        response = self.client.responses.parse(
            agent_id=self.agent_id,
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": input_payload,
                        }
                    ],
                }
            ],
            response_format=self.output_model,
        )
        if hasattr(response, "output"):
            return response.output[0]
        if isinstance(response, self.output_model):
            return response
        # Fallback: parse raw JSON string
        if hasattr(response, "output") and response.output:
            content = response.output[0]
            if hasattr(content, "content"):
                raw = content.content[0].text
            else:
                raw = json.dumps(response.output)
        else:
            raw = str(response)
        return self.output_model.model_validate_json(raw)
