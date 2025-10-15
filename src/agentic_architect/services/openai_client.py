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

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        request_payload: Dict[str, Any] = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_output_tokens,
        }
        request_payload.update(extra)
        return self._client.chat.completions.create(**request_payload)


__all__ = ["OpenAIClient"]
