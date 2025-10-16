"""Simplified Mailgun HTTP client."""
from __future__ import annotations

from typing import Dict


class MailgunClient:
    def send(self, subject: str, body: str, recipients: list[str]) -> Dict[str, str]:
        return {"provider": "mailgun", "status": "queued", "recipient_count": str(len(recipients))}
