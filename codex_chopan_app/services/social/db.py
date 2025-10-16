"""In-memory store for scheduled posts and metrics."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List


@dataclass
class SocialPost:
    post_id: str
    network: str
    message: str
    scheduled_time: datetime
    status: str = "scheduled"
    metrics: Dict[str, float] = field(default_factory=dict)


class SocialRepository:
    def __init__(self) -> None:
        self._posts: Dict[str, SocialPost] = {}

    def save(self, post: SocialPost) -> SocialPost:
        self._posts[post.post_id] = post
        return post

    def list_network(self, network: str) -> List[SocialPost]:
        return [post for post in self._posts.values() if post.network == network]
