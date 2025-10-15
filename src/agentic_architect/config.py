"""Application configuration using Pydantic settings."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class OpenAIConfig(BaseModel):
    """Configuration for the OpenAI Agentic SDK."""

    api_key: str = Field(default_factory=lambda: "")
    base_url: Optional[str] = None
    model: str = "kimi-k2-0905-preview"
    temperature: float = 0.2
    max_output_tokens: int = 4096


class DatabaseConfig(BaseModel):
    """Configuration for the SQLite database used for coordination and caching."""

    url: str = Field(default="sqlite:///agentic_architect.db")
    echo: bool = False


class ResearchConfig(BaseModel):
    """Configuration for web research behaviour."""

    max_results: int = 5
    cache_ttl_hours: int = 24


class Settings(BaseSettings):
    """Central application settings."""

    model_config = SettingsConfigDict(env_prefix="AGENTIC_", env_file=(Path(".env"), Path("~/.agentic-architect")))

    openai: OpenAIConfig = Field(default_factory=OpenAIConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    research: ResearchConfig = Field(default_factory=ResearchConfig)
    workspace_root: Path = Field(default=Path.cwd())

    def to_dict(self) -> Dict[str, Any]:
        """Return settings as a dictionary."""

        return {
            "openai": self.openai.model_dump(),
            "database": self.database.model_dump(),
            "research": self.research.model_dump(),
            "workspace_root": str(self.workspace_root),
        }


__all__ = ["Settings", "OpenAIConfig", "DatabaseConfig", "ResearchConfig"]
