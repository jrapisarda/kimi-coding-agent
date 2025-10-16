"""Filesystem snapshot utilities."""
from __future__ import annotations

import shutil
import tempfile
import zipfile
from pathlib import Path


class SnapshotManager:
    """Creates and restores workspace snapshots for rollback safety."""

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def create_snapshot(self, run_id: str, target_path: Path) -> Path:
        """Zip the target directory and store it in the snapshot directory."""

        snapshot_path = self.base_dir / f"{run_id}.zip"
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_base = Path(tmpdir) / run_id
            shutil.make_archive(str(temp_base), "zip", target_path)
            shutil.move(str(temp_base) + ".zip", snapshot_path)
        return snapshot_path

    def restore_snapshot(self, snapshot_path: Path, target_path: Path) -> None:
        """Restore a previously captured snapshot."""

        if not snapshot_path.exists():
            return
        if target_path.exists():
            for entry in target_path.iterdir():
                if entry.is_dir():
                    shutil.rmtree(entry)
                else:
                    entry.unlink()
        else:
            target_path.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(snapshot_path, "r") as archive:
            archive.extractall(target_path)

    def cleanup_snapshot(self, snapshot_path: Path) -> None:
        if snapshot_path.exists():
            snapshot_path.unlink()
