"""OpenAI client helper that ensures the newest Agents SDK patterns are used."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any, Iterable, Optional

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


def _agents_resource(client: OpenAI) -> Any:
    """Return the Agents API resource from the OpenAI client.

    The SDK transitioned from ``client.beta.agents`` to ``client.agents``. Users
    on older versions (for example, 1.51 and earlier) will only have the beta
    namespace, while newer versions expose ``client.agents`` directly. This
    helper normalizes access and provides a clear error message when neither is
    available.
    """

    if hasattr(client, "agents") and client.agents is not None:  # type: ignore[attr-defined]
        return client.agents

    beta = getattr(client, "beta", None)
    if beta is not None and hasattr(beta, "agents"):
        return beta.agents

    raise RuntimeError(
        "The configured OpenAI client does not expose the Agents API. Upgrade the"
        " `openai` package to >=1.51.0 or provide a compatible client via"
        " `KIMI_AGENT_OPENAI_CLIENT_FACTORY`."
    )


def create_agent_if_needed(client: OpenAI, name: str, instructions: str, tools: Iterable[dict], model: Optional[str] = None) -> str:
    """Create an ephemeral agent for the run if one is not already provided."""

    model = model or _selected_model()
    agents = _agents_resource(client)
    response = agents.create(
        name=name,
        model=model,
        instructions=instructions,
        tools=list(tools),
    )
    return response.id
