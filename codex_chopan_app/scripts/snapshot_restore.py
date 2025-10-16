"""CLI to restore snapshots."""
from __future__ import annotations

import argparse

from codex_chopan_app.services.prospect.main import get_service


def main() -> None:
    parser = argparse.ArgumentParser(description="Restore a snapshot by ID")
    parser.add_argument("--to", required=True, dest="target_id")
    args = parser.parse_args()

    service = get_service()
    snapshot = service.restore_snapshot(args.target_id)
    print(f"Restored snapshot {snapshot.snapshot_id} containing {len(snapshot.artifacts)} artifacts")


if __name__ == "__main__":  # pragma: no cover
    main()
