"""Email service unit tests."""
from __future__ import annotations

from codex_chopan_app.services.email.main import CampaignRequest, EmailService, _service


def test_campaign_suppression() -> None:
    service: EmailService = _service
    request = CampaignRequest(
        subject="Hello",
        audience_segment=["one@example.com", "two@example.com"],
        body="Hi",
        suppression_list=["two@example.com"],
    )
    campaign = service.create_campaign(request)
    assert campaign.suppressed == ["two@example.com"]
