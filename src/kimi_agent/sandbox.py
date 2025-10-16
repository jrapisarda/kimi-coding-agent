"""Workspace snapshot and rollback manager."""

from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class Snapshot:
    path: Path


class SandboxManager:
    """Manage workspace snapshots and rollbacks."""

    def __init__(self, target_path: Path) -> None:
        self.target_path = target_path
        self._snapshot: Optional[Snapshot] = None

    def create_snapshot(self) -> Snapshot:
        temp_dir = Path(tempfile.mkdtemp(prefix="kimi-agent-snapshot-"))
        snapshot_path = temp_dir / "workspace"
        shutil.copytree(self.target_path, snapshot_path)
        self._snapshot = Snapshot(path=snapshot_path)
        return self._snapshot

    def restore_snapshot(self) -> None:
        if not self._snapshot:
            return
        shutil.rmtree(self.target_path, ignore_errors=True)
        shutil.copytree(self._snapshot.path, self.target_path)

    def cleanup(self) -> None:
        if self._snapshot:
            shutil.rmtree(self._snapshot.path.parent, ignore_errors=True)
            self._snapshot = None
