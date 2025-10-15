"""Utilities for interacting with the OpenAI Agentic SDK."""

from __future__ import annotations

from typing import Any, Dict, Optional

from openai import OpenAI

from ..config import OpenAIConfig


class OpenAIClient:
    """Wrapper around the OpenAI client that standardises request parameters."""

    def __init__(self, config: OpenAIConfig) -> None:
        self.config = config
        kwargs: Dict[str, Any] = {}
        if config.base_url:
            kwargs["base_url"] = config.base_url
        if config.api_key:
            kwargs["api_key"] = config.api_key
        self._client = OpenAI(**kwargs)

    def create_response(self, prompt: str, *, system_prompt: Optional[str] = None, **extra: Any) -> Any:
        """Call the response endpoint with sensible defaults."""

        request_payload: Dict[str, Any] = {
            "model": self.config.model,
            "input": prompt,
            "temperature": self.config.temperature,
            "max_output_tokens": self.config.max_output_tokens,
        }
        if system_prompt:
            request_payload["system"] = system_prompt
        request_payload.update(extra)
        return self._client.responses.create(**request_payload)


__all__ = ["OpenAIClient"]
