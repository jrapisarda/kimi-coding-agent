"""API gateway routes that orchestrate downstream services."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from ..content.main import ContentRequest, ContentService, get_service as get_content_service
from ..email.main import CampaignRequest, EmailService, WebhookRequest, get_service as get_email_service
from ..prospect.main import ProspectRequest, ProspectService, get_service as get_prospect_service
from ..social.main import ScheduleRequest, SocialService, get_service as get_social_service
from ..worker import tasks
from .auth import require_api_key
from .models import (
    ContentDraftRequest,
    ContentDraftResponse,
    EmailCampaignRequest,
    EmailCampaignResponse,
    ProspectResponse,
    ProspectSeedRequest,
    SnapshotCreateResponse,
    SnapshotRestoreRequest,
    SnapshotRestoreResponse,
    SocialPostRequest,
    SocialPostResponse,
)
from .rate_limiter import SlidingWindowRateLimiter

router = APIRouter()
limiter = SlidingWindowRateLimiter(max_requests=60, window_seconds=60.0)


async def enforce_rate_limit() -> None:
    allowed = await limiter.allow("global")
    if not allowed:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")


@router.get("/health")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@router.post("/content/draft", response_model=ContentDraftResponse)
async def create_content_draft(
    payload: ContentDraftRequest,
    _: str = Depends(require_api_key),
    __: None = Depends(enforce_rate_limit),
    service: ContentService = Depends(get_content_service),
) -> ContentDraftResponse:
    request = ContentRequest(
        brief=payload.brief,
        language=payload.language,
        tone=payload.tone,
        scheduled_time=None,
    )
    draft = service.create_draft(request)
    moderation_passed = getattr(draft, "moderation_passed", True)
    return ContentDraftResponse(
        draft_id=draft.draft_id,
        content=draft.content,
        language=draft.language,
        moderation_passed=moderation_passed,
        scheduled_time=draft.scheduled_time,
    )


@router.post("/email/campaign", response_model=EmailCampaignResponse)
async def create_email_campaign(
    payload: EmailCampaignRequest,
    _: str = Depends(require_api_key),
    __: None = Depends(enforce_rate_limit),
    service: EmailService = Depends(get_email_service),
) -> EmailCampaignResponse:
    request = CampaignRequest(**payload.model_dump())
    campaign = service.create_campaign(request)
    return EmailCampaignResponse(
        campaign_id=campaign.campaign_id,
        suppressed=campaign.suppressed,
        scheduled_at=campaign.scheduled_at,
    )


@router.post("/email/webhooks")
async def ingest_email_webhooks(
    payload: dict,
    _: str = Depends(require_api_key),
    __: None = Depends(enforce_rate_limit),
    service: EmailService = Depends(get_email_service),
) -> list[dict[str, str]]:
    request = WebhookRequest(events=list(payload.get("events", [])))
    return service.ingest_webhooks(request)


@router.post("/social/schedule", response_model=SocialPostResponse)
async def schedule_social_post(
    payload: SocialPostRequest,
    _: str = Depends(require_api_key),
    __: None = Depends(enforce_rate_limit),
    service: SocialService = Depends(get_social_service),
) -> SocialPostResponse:
    request = ScheduleRequest(**payload.model_dump())
    post = service.schedule(request)
    return SocialPostResponse(
        post_id=post.post_id,
        network=post.network,
        scheduled_time=post.scheduled_time,
        status=post.status,
    )


@router.get("/social/metrics/{network}")
async def get_social_metrics(
    network: str,
    _: str = Depends(require_api_key),
    __: None = Depends(enforce_rate_limit),
    service: SocialService = Depends(get_social_service),
) -> list[dict[str, float | str]]:
    metrics = service.metrics(network)
    return [
        {
            "post_id": post.post_id,
            "status": post.status,
            "clicks": post.metrics.get("clicks", 0.0),
            "impressions": post.metrics.get("impressions", 0.0),
        }
        for post in metrics
    ]


@router.post("/prospect/discover", response_model=list[ProspectResponse])
async def discover_prospects(
    payload: ProspectSeedRequest,
    _: str = Depends(require_api_key),
    __: None = Depends(enforce_rate_limit),
    service: ProspectService = Depends(get_prospect_service),
) -> list[ProspectResponse]:
    request = ProspectRequest(**payload.model_dump())
    results = service.discover(request.query, request.limit)
    return [
        ProspectResponse(
            organization=item.organization,
            score=item.score,
            website=item.website,
            provenance_key=item.provenance_key,
        )
        for item in results
    ]


@router.post("/snapshots", response_model=SnapshotCreateResponse)
async def create_snapshot(
    artifacts: list[dict[str, str]],
    _: str = Depends(require_api_key),
    __: None = Depends(enforce_rate_limit),
    service: ProspectService = Depends(get_prospect_service),
) -> SnapshotCreateResponse:
    snapshot = service.create_snapshot(artifacts)
    return SnapshotCreateResponse(
        snapshot_id=snapshot.snapshot_id,
        stored_at=snapshot.stored_at,
        artifact_count=len(snapshot.artifacts),
    )


@router.post("/snapshots/restore", response_model=SnapshotRestoreResponse)
async def restore_snapshot(
    payload: SnapshotRestoreRequest,
    _: str = Depends(require_api_key),
    __: None = Depends(enforce_rate_limit),
    service: ProspectService = Depends(get_prospect_service),
) -> SnapshotRestoreResponse:
    snapshot = service.restore_snapshot(payload.target_id)
    return SnapshotRestoreResponse(
        restored=True,
        restored_at=datetime.utcnow(),
        details=f"Restored {len(snapshot.artifacts)} artifacts",
    )


@router.post("/tasks/content")
async def trigger_content_task(brief: str, _: str = Depends(require_api_key)) -> dict[str, str]:
    result = tasks.generate_content(brief)
    return result
