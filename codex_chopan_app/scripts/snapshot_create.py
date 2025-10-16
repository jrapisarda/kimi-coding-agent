"""CLI to create snapshots via the prospect service."""
from __future__ import annotations

import argparse
from datetime import datetime

from codex_chopan_app.services.prospect.main import get_service


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a snapshot of prospect artifacts")
    parser.add_argument("--artifact", action="append", nargs=2, metavar=("key", "value"), help="Key/value pair")
    args = parser.parse_args()

    artifacts = []
    if args.artifact:
        for key, value in args.artifact:
            artifacts.append({key: value, "timestamp": datetime.utcnow().isoformat()})

    service = get_service()
    snapshot = service.create_snapshot(artifacts or [{"note": "empty"}])
    print(f"Created snapshot {snapshot.snapshot_id} with {len(snapshot.artifacts)} artifacts")


if __name__ == "__main__":  # pragma: no cover - CLI entry
    main()
