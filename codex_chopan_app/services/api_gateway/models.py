"""Pydantic models shared across API gateway routes."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, HttpUrl


class ContentDraftRequest(BaseModel):
    brief: str = Field(..., min_length=1, description="Short description of the content goal")
    language: str = Field(default="en", description="Desired language for the draft")
    tone: str | None = Field(default=None, description="Optional tone guidance")


class ContentDraftResponse(BaseModel):
    draft_id: str
    content: str
    language: str
    moderation_passed: bool
    scheduled_time: Optional[datetime] = None


class EmailCampaignRequest(BaseModel):
    subject: str
    audience_segment: List[str]
    body: str
    suppression_list: List[str] = Field(default_factory=list)


class EmailCampaignResponse(BaseModel):
    campaign_id: str
    suppressed: List[str]
    scheduled_at: datetime


class SocialPostRequest(BaseModel):
    network: str = Field(description="Destination social network, e.g. linkedin")
    message: str
    scheduled_time: Optional[datetime] = None


class SocialPostResponse(BaseModel):
    post_id: str
    network: str
    scheduled_time: datetime
    status: str


class ProspectSeedRequest(BaseModel):
    query: str
    limit: int = Field(default=3, ge=1, le=10)


class ProspectResponse(BaseModel):
    organization: str
    score: float
    website: HttpUrl
    provenance_key: str


class SnapshotCreateResponse(BaseModel):
    snapshot_id: str
    stored_at: datetime
    artifact_count: int


class SnapshotRestoreRequest(BaseModel):
    target_id: str


class SnapshotRestoreResponse(BaseModel):
    restored: bool
    restored_at: datetime
    details: str
