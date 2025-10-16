# Rollback Runbook

1. Identify snapshot ID from `snapshots/` manifest or S3 inventory.
2. Run `python scripts/snapshot_restore.py --to <snapshot_id>`.
3. Validate restored data against audit manifest.
4. Notify stakeholders of rollback scope and timing.
5. Schedule post-incident review.
