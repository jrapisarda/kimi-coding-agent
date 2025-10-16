"""Runtime configuration utilities."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class Settings:
    """Static configuration for orchestrator components."""

    state_dir: Path = Path.home() / ".kimi_coding_agent"
    database_file: Path | None = None

    def resolve_database_path(self) -> Path:
        """Return the SQLite database path, creating directories as needed."""

        if self.database_file is not None:
            db_path = self.database_file
        else:
            db_path = self.state_dir / "runs.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return db_path


DEFAULT_SETTINGS = Settings()
