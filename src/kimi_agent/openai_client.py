"""OpenAI client helper that ensures the newest Agents SDK patterns are used."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Iterable, Optional

from openai import OpenAI

from .config import DEFAULT_MODEL


def _selected_model() -> str:
    return os.getenv("KIMI_AGENT_MODEL", DEFAULT_MODEL)


@lru_cache(maxsize=1)
def get_openai_client() -> OpenAI:
    """Return a cached OpenAI client."""

    client = OpenAI()
    return client


def prepare_tools(enable_code_interpreter: bool, enable_web_search: bool, enable_file_search: bool) -> Iterable[dict]:
    """Build tool configuration payloads for the Agents SDK."""

    tools = []
    if enable_code_interpreter:
        tools.append({"type": "code_interpreter"})
    if enable_web_search:
        tools.append({"type": "web_search"})
    if enable_file_search:
        tools.append({"type": "file_search"})
    return tools


def create_agent_if_needed(client: OpenAI, name: str, instructions: str, tools: Iterable[dict], model: Optional[str] = None) -> str:
    """Create an ephemeral agent for the run if one is not already provided."""

    model = model or _selected_model()
    response = client.agents.create(
        name=name,
        model=model,
        instructions=instructions,
        tools=list(tools),
    )
    return response.id
