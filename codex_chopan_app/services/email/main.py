"""FastAPI application exposing email campaign orchestration."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List
from uuid import uuid4

from fastapi import Depends, FastAPI
from pydantic import BaseModel, Field

from .db import EmailCampaign, EmailRepository
from .mailgun_client import MailgunClient
from .sendgrid_client import SendGridClient
from .webhooks import WebhookEvent, normalize_events


class CampaignRequest(BaseModel):
    subject: str
    audience_segment: List[str]
    body: str
    suppression_list: List[str] = Field(default_factory=list)


class WebhookRequest(BaseModel):
    events: List[dict[str, str]]


class EmailService:
    def __init__(self, repository: EmailRepository) -> None:
        self.repository = repository
        self.sendgrid = SendGridClient()
        self.mailgun = MailgunClient()

    def create_campaign(self, request: CampaignRequest) -> EmailCampaign:
        suppressed = [email for email in request.audience_segment if email in request.suppression_list]
        recipients = [email for email in request.audience_segment if email not in suppressed]
        campaign = EmailCampaign(
            campaign_id=str(uuid4()),
            subject=request.subject,
            audience_segment=request.audience_segment,
            body=request.body,
            suppressed=suppressed,
            scheduled_at=datetime.utcnow() + timedelta(hours=2),
        )
        self.repository.save(campaign)
        if recipients:
            self.sendgrid.send(campaign.subject, campaign.body, recipients)
        return campaign

    def ingest_webhooks(self, payload: WebhookRequest) -> List[dict[str, str]]:
        events = [
            WebhookEvent(
                provider=item.get("provider", "unknown"),
                event_type=item.get("event", "unknown"),
                recipient=item.get("recipient", ""),
                timestamp=datetime.fromisoformat(item.get("ts", datetime.utcnow().isoformat())),
            )
            for item in payload.events
        ]
        return normalize_events(events)


_repo = EmailRepository()
_service = EmailService(_repo)

app = FastAPI(title="Email Service", version="1.0.0")


def get_service() -> EmailService:
    return _service


@app.post("/campaign")
async def create_campaign(request: CampaignRequest, service: EmailService = Depends(get_service)) -> Dict[str, str]:
    campaign = service.create_campaign(request)
    return {
        "campaign_id": campaign.campaign_id,
        "suppressed": campaign.suppressed,
        "scheduled_at": campaign.scheduled_at.isoformat(),
    }


@app.post("/webhooks")
async def ingest_webhooks(request: WebhookRequest, service: EmailService = Depends(get_service)) -> List[dict[str, str]]:
    return service.ingest_webhooks(request)
