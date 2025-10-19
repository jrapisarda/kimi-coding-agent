from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class SandboxPolicy:
    """Control which sandboxed commands are permissible."""

    allow_cli_tools: bool = False
    allow_package_installs: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "allow_cli_tools": self.allow_cli_tools,
            "allow_package_installs": self.allow_package_installs,
        }


@dataclass
class OpenAIConfig:
    """Configuration describing how the orchestrator will call the OpenAI APIs."""

    model: str = "gpt-5-mini"
    temperature: float = 0.2
    max_output_tokens: int = 4096
    enabled: bool = True
    api_key_env: str = "OPENAI_API_KEY"
    base_url: Optional[str] = None


@dataclass
class PathsConfig:
    """Filesystem layout for the agent run."""

    root: Path
    data_dir: Path
    dist_dir: Path
    db_path: Path


@dataclass
class AppConfig:
    """Top level configuration consumed throughout the pipeline."""

    environment: str = "local"
    dry_run: bool = False
    paths: PathsConfig = field(default_factory=lambda: build_paths(Path.cwd()))
    openai: OpenAIConfig = field(default_factory=OpenAIConfig)
    sandbox: SandboxPolicy = field(default_factory=SandboxPolicy)

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON serialisable copy of the config for persistence."""
        payload = asdict(self)
        payload["paths"] = {
            "root": str(self.paths.root),
            "data_dir": str(self.paths.data_dir),
            "dist_dir": str(self.paths.dist_dir),
            "db_path": str(self.paths.db_path),
        }
        payload["sandbox"] = self.sandbox.to_dict()
        return payload


def build_paths(root: Path) -> PathsConfig:
    """Construct the default filesystem layout under *root*."""
    data_dir = root / "var"
    dist_dir = root / "dist"
    db_path = data_dir / "runs.sqlite"
    return PathsConfig(root=root, data_dir=data_dir, dist_dir=dist_dir, db_path=db_path)


def load_config(path: Optional[Path], dry_run: bool = False) -> AppConfig:
    """
    Load configuration from *path* if provided, otherwise use repository defaults.

    The configuration file is expected to be JSON. Unspecified fields will fall back
    to the defaults baked into the dataclasses above.
    """
    config = AppConfig()
    config.paths = build_paths(Path.cwd())
    config.dry_run = dry_run

    if path is None:
        return config

    with Path(path).expanduser().open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    _apply_config_updates(config, data)
    config.dry_run = dry_run or data.get("dry_run", config.dry_run)
    return config


def _apply_config_updates(config: AppConfig, payload: Dict[str, Any]) -> None:
    """Update *config* in-place using keys from the *payload* dict."""
    if "environment" in payload:
        config.environment = payload["environment"]

    if "openai" in payload:
        for key, value in payload["openai"].items():
            if hasattr(config.openai, key):
                setattr(config.openai, key, value)

    if "paths" in payload:
        override = payload["paths"]
        root = Path(override.get("root", config.paths.root))
        paths = build_paths(root)
        if "data_dir" in override:
            paths.data_dir = Path(override["data_dir"])
        if "dist_dir" in override:
            paths.dist_dir = Path(override["dist_dir"])
        if "db_path" in override:
            paths.db_path = Path(override["db_path"])
        config.paths = paths

    if "sandbox" in payload:
        for key, value in payload["sandbox"].items():
            if hasattr(config.sandbox, key):
                setattr(config.sandbox, key, value)
