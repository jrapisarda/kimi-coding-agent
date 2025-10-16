"""Social service unit tests."""
from __future__ import annotations

from datetime import datetime, timedelta

from codex_chopan_app.services.social.main import ScheduleRequest, SocialService, _service


def test_schedule_publishes_when_past() -> None:
    service: SocialService = _service
    request = ScheduleRequest(network="linkedin", message="Hello", scheduled_time=datetime.utcnow() - timedelta(minutes=1))
    post = service.schedule(request)
    assert post.status == "published"
