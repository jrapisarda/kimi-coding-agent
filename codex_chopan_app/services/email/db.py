"""In-memory store for email campaigns."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List


@dataclass
class EmailCampaign:
    campaign_id: str
    subject: str
    audience_segment: List[str]
    body: str
    suppressed: List[str] = field(default_factory=list)
    scheduled_at: datetime = field(default_factory=datetime.utcnow)


class EmailRepository:
    def __init__(self) -> None:
        self._campaigns: Dict[str, EmailCampaign] = {}

    def save(self, campaign: EmailCampaign) -> EmailCampaign:
        self._campaigns[campaign.campaign_id] = campaign
        return campaign

    def get(self, campaign_id: str) -> EmailCampaign:
        return self._campaigns[campaign_id]

    def list_all(self) -> List[EmailCampaign]:
        return list(self._campaigns.values())
