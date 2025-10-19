from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any, Optional

from ..config import OpenAIConfig


LOGGER = logging.getLogger("kimi_agent.openai")


@dataclass
class OpenAIClient:
    """Thin wrapper around OpenAI's Responses API with graceful fallbacks."""

    model: str
    temperature: float
    max_output_tokens: Optional[int]
    enabled: bool
    dry_run: bool
    api_key_env: str = "OPENAI_API_KEY"
    base_url: Optional[str] = None
    timeout: float = 60.0
    _client: Optional[Any] = field(default=None, init=False, repr=False)
    _api_key: Optional[str] = field(default=None, init=False, repr=False)

    def generate_text(self, prompt: str) -> str:
        if not self.enabled or self.dry_run:
            LOGGER.debug("OpenAI client in dry mode - returning stub content for prompt: %s", prompt)
            return f"[stubbed response for model {self.model}] {prompt}"
        api_key = os.getenv(self.api_key_env)
        if not api_key:
            LOGGER.warning("%s not set - falling back to stubbed response.", self.api_key_env)
            return f"[missing api key for model {self.model}] {prompt}"

        client = self._ensure_client(api_key)
        request_params = {
            "model": self.model,
            "input": prompt,
            "temperature": self.temperature,
        }
        if self.max_output_tokens is not None:
            request_params["max_output_tokens"] = self.max_output_tokens
        try:
            LOGGER.debug("Invoking OpenAI Responses API with model %s", self.model)
            response = client.responses.create(**request_params)
        except Exception as exc:  # pragma: no cover - network/SDK runtime errors
            LOGGER.exception("OpenAI API call failed: %s", exc)
            return f"[openai error for model {self.model}: {exc}] {prompt}"

        text = self._extract_text(response)
        if not text:
            LOGGER.warning("OpenAI response contained no text output; returning raw response repr.")
            text = str(response)
        return text

    def _ensure_client(self, api_key: str):
        if self._client is not None and self._api_key == api_key:
            return self._client
        try:
            from openai import OpenAI  # type: ignore import-not-found
        except ImportError as exc:  # pragma: no cover - handled via dependency management
            LOGGER.exception("openai package is not installed. Please add 'openai' to your dependencies.")
            raise RuntimeError("OpenAI SDK is required for real integration.") from exc

        base_url = self.base_url or os.getenv("OPENAI_BASE_URL")
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        client = OpenAI(**kwargs)
        if self.timeout:
            client = client.with_options(timeout=self.timeout)
        self._client = client
        self._api_key = api_key
        return self._client

    @staticmethod
    def _extract_text(response: Any) -> str:
        if response is None:
            return ""
        output_text = getattr(response, "output_text", None)
        if isinstance(output_text, str) and output_text.strip():
            return output_text.strip()

        chunks = []
        output = getattr(response, "output", None)
        if output:
            for item in output:
                item_type = getattr(item, "type", None) or item.get("type") if isinstance(item, dict) else None
                if item_type != "message":
                    continue
                contents = getattr(item, "content", None)
                if isinstance(contents, list):
                    for content in contents:
                        text = OpenAIClient._extract_text_from_content(content)
                        if text:
                            chunks.append(text)
                elif isinstance(contents, str):
                    chunks.append(contents)

        if not chunks:
            choices = getattr(response, "choices", None)
            if choices:
                for choice in choices:
                    message = getattr(choice, "message", None)
                    if isinstance(message, dict):
                        content = message.get("content")
                        if isinstance(content, str):
                            chunks.append(content)
                        elif isinstance(content, list):
                            for segment in content:
                                text = OpenAIClient._extract_text_from_content(segment)
                                if text:
                                    chunks.append(text)
                    elif message and isinstance(message, str):
                        chunks.append(message)
        return "\n".join(chunk.strip() for chunk in chunks if isinstance(chunk, str) and chunk.strip())

    @staticmethod
    def _extract_text_from_content(content: Any) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, dict):
            if content.get("type") == "text":
                text = content.get("text")
                if isinstance(text, str):
                    return text
        return ""


class OpenAIClientFactory:
    """Factory for creating `OpenAIClient` instances from configuration."""

    @staticmethod
    def create(config: OpenAIConfig, dry_run: bool) -> OpenAIClient:
        return OpenAIClient(
            model=config.model,
            temperature=config.temperature,
            max_output_tokens=config.max_output_tokens,
            enabled=config.enabled,
            dry_run=dry_run or not config.enabled,
            api_key_env=config.api_key_env,
            base_url=config.base_url,
        )
