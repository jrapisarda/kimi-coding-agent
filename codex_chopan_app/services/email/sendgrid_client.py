"""Simplified SendGrid HTTP client."""
from __future__ import annotations

from typing import Dict


class SendGridClient:
    def send(self, subject: str, body: str, recipients: list[str]) -> Dict[str, str]:
        return {"provider": "sendgrid", "status": "queued", "recipient_count": str(len(recipients))}
