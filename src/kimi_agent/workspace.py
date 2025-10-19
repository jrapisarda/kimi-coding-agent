from __future__ import annotations

import logging
import shutil
import zipfile
from pathlib import Path
from typing import Optional


LOGGER = logging.getLogger("kimi_agent.workspace")


class WorkspaceManager:
    """Handle snapshot and rollback operations around agent runs."""

    def __init__(self, data_dir: Path) -> None:
        self._snapshots_dir = Path(data_dir) / "snapshots"
        self._restores_dir = Path(data_dir) / "restores"
        self._snapshots_dir.mkdir(parents=True, exist_ok=True)
        self._restores_dir.mkdir(parents=True, exist_ok=True)

    def create_snapshot(self, run_id: str, target_path: Path) -> Optional[Path]:
        """Create a zip snapshot of the target workspace."""
        target = Path(target_path)
        if not target.exists():
            LOGGER.info("Workspace snapshot skipped; %s does not exist.", target)
            return None

        snapshot_path = self._snapshots_dir / f"{run_id}.zip"
        if snapshot_path.exists():
            snapshot_path.unlink()

        LOGGER.info("Creating workspace snapshot at %s", snapshot_path)
        shutil.make_archive(
            base_name=str(snapshot_path.with_suffix("")),
            format="zip",
            root_dir=target,
        )
        return snapshot_path

    def stage_restore(self, run_id: str, snapshot_path: Optional[Path]) -> Optional[Path]:
        """
        Extract the snapshot into a dedicated restore directory.

        The current implementation avoids mutating the original workspace directly and instead
        prepares a restored copy for manual inspection or scripted future automation.
        """
        if not snapshot_path or not Path(snapshot_path).exists():
            LOGGER.warning("No snapshot available to restore for run %s.", run_id)
            return None

        restore_dir = self._restores_dir / run_id
        if restore_dir.exists():
            shutil.rmtree(restore_dir)
        restore_dir.mkdir(parents=True, exist_ok=True)

        LOGGER.warning("Restoring workspace snapshot to %s", restore_dir)
        with zipfile.ZipFile(snapshot_path, "r") as archive:
            archive.extractall(restore_dir)
        return restore_dir
