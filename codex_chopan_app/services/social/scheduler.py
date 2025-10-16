"""Scheduling helpers for social posts."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional


def compute_schedule(scheduled_time: Optional[datetime]) -> datetime:
    return scheduled_time or datetime.utcnow() + timedelta(minutes=15)
