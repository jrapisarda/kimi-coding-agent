"""FastAPI application exposing the social scheduling service."""
from __future__ import annotations

from datetime import datetime
from typing import Dict
from uuid import uuid4

from fastapi import Depends, FastAPI
from pydantic import BaseModel

from .db import SocialPost, SocialRepository
from .linkedin_client import LinkedInClient
from .meta_client import MetaClient
from .scheduler import compute_schedule


class ScheduleRequest(BaseModel):
    network: str
    message: str
    scheduled_time: datetime | None = None


class SocialService:
    def __init__(self, repository: SocialRepository) -> None:
        self.repository = repository
        self.meta = MetaClient()
        self.linkedin = LinkedInClient()

    def _publish(self, network: str, message: str) -> Dict[str, str]:
        if network.lower() == "meta":
            return self.meta.publish(message)
        return self.linkedin.publish(message)

    def schedule(self, request: ScheduleRequest) -> SocialPost:
        scheduled_time = compute_schedule(request.scheduled_time)
        post = SocialPost(
            post_id=str(uuid4()),
            network=request.network.lower(),
            message=request.message,
            scheduled_time=scheduled_time,
        )
        if scheduled_time <= datetime.utcnow():
            post.status = "published"
            post.metrics = {"clicks": 10.0, "impressions": 120.0}
            self._publish(post.network, post.message)
        return self.repository.save(post)

    def metrics(self, network: str) -> list[SocialPost]:
        posts = self.repository.list_network(network.lower())
        for post in posts:
            if post.status == "scheduled" and post.scheduled_time <= datetime.utcnow():
                post.status = "published"
                post.metrics = {"clicks": 5.0, "impressions": 50.0}
        return posts


_repo = SocialRepository()
_service = SocialService(_repo)

app = FastAPI(title="Social Service", version="1.0.0")


def get_service() -> SocialService:
    return _service


@app.post("/schedule")
async def schedule_post(request: ScheduleRequest, service: SocialService = Depends(get_service)) -> Dict[str, str]:
    post = service.schedule(request)
    return {
        "post_id": post.post_id,
        "network": post.network,
        "scheduled_time": post.scheduled_time.isoformat(),
        "status": post.status,
    }


@app.get("/metrics/{network}")
async def get_metrics(network: str, service: SocialService = Depends(get_service)) -> list[Dict[str, float | str]]:
    return [
        {
            "post_id": post.post_id,
            "status": post.status,
            "clicks": post.metrics.get("clicks", 0.0),
            "impressions": post.metrics.get("impressions", 0.0),
        }
        for post in service.metrics(network)
    ]
