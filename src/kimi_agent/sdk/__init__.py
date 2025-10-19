"""
SDK glue that wraps the OpenAI Responses/Agents APIs.

Sprint one exposes a stubbed client that logs intended calls so that future
integration can be implemented with minimal churn.
"""

from .openai_client import OpenAIClient, OpenAIClientFactory

__all__ = ["OpenAIClient", "OpenAIClientFactory"]
