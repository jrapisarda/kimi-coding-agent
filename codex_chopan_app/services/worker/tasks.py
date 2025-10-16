"""Celery tasks for asynchronous workflows."""
from __future__ import annotations

from datetime import datetime

from .celery_app import app
from .queues import CONTENT_QUEUE, EMAIL_QUEUE, PROSPECT_QUEUE, SOCIAL_QUEUE


@app.task(name="content.generate", queue=CONTENT_QUEUE)
def generate_content(brief: str) -> dict[str, str]:
    return {"draft": brief.upper(), "generated_at": datetime.utcnow().isoformat()}


@app.task(name="email.retry", queue=EMAIL_QUEUE)
def email_retry(campaign_id: str, attempt: int) -> dict[str, str]:
    return {"campaign_id": campaign_id, "attempt": str(attempt)}


@app.task(name="social.refresh", queue=SOCIAL_QUEUE)
def social_refresh(network: str) -> dict[str, str]:
    return {"network": network, "refreshed": datetime.utcnow().isoformat()}


@app.task(name="prospect.score", queue=PROSPECT_QUEUE)
def prospect_score(org_name: str, base_score: float) -> dict[str, str]:
    adjusted = base_score + 0.1
    return {"organization": org_name, "score": f"{adjusted:.2f}"}
