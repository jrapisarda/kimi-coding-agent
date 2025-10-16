"""Packaging helpers for bundling run artifacts."""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Dict


class RunPackager:
    """Produces dist/<run_id>.zip archives with run metadata."""

    def __init__(self, dist_dir: Path) -> None:
        self.dist_dir = dist_dir
        self.dist_dir.mkdir(parents=True, exist_ok=True)

    def package(self, run_id: str, target_path: Path, contexts: Dict[str, Any]) -> Path:
        metadata_path = target_path / f"agent_run_{run_id}.json"
        metadata_path.write_text(json.dumps(contexts, indent=2, default=str), encoding="utf-8")
        archive_base = self.dist_dir / run_id
        archive_path = archive_base.with_suffix(".zip")
        if archive_path.exists():
            archive_path.unlink()
        shutil.make_archive(str(archive_base), "zip", target_path)
        return archive_path
