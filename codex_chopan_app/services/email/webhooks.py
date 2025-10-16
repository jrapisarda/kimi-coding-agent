"""Webhook ingestion helpers."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List


@dataclass
class WebhookEvent:
    provider: str
    event_type: str
    recipient: str
    timestamp: datetime


def normalize_events(events: List[WebhookEvent]) -> List[dict[str, str]]:
    return [
        {
            "provider": event.provider,
            "event": event.event_type,
            "recipient": event.recipient,
            "ts": event.timestamp.isoformat(),
        }
        for event in events
    ]
