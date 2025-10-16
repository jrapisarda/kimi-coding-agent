"""FastAPI application exposing prospect discovery."""
from __future__ import annotations

from datetime import datetime
from typing import List
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel

from .cse_client import CustomSearchClient
from .db import Prospect, ProspectRepository
from .features import extract_features
from .robots import is_allowed
from .scoring import score
from .snapshot_s3 import Snapshot, SnapshotStore


class ProspectRequest(BaseModel):
    query: str
    limit: int = 3


class SnapshotRequest(BaseModel):
    artifacts: List[dict[str, str]]


class ProspectService:
    def __init__(self, repository: ProspectRepository, snapshot_store: SnapshotStore) -> None:
        self.repository = repository
        self.snapshot_store = snapshot_store
        self.search_client = CustomSearchClient()

    def discover(self, query: str, limit: int) -> List[Prospect]:
        raw_results = self.search_client.search(query, limit)
        prospects: List[Prospect] = []
        for result in raw_results:
            website = result["website"]
            if not is_allowed(website):
                raise HTTPException(status_code=400, detail=f"Robots.txt forbids crawling {website}")
            features = extract_features(result["organization"])
            prospect_score = score(features)
            prospect = Prospect(
                organization=result["organization"],
                website=website,
                score=prospect_score,
                provenance_key=str(uuid4()),
                discovered_at=datetime.utcnow(),
            )
            self.repository.save(prospect)
            prospects.append(prospect)
        self.snapshot_store.create([result for result in raw_results])
        return prospects

    def create_snapshot(self, artifacts: List[dict[str, str]]) -> Snapshot:
        return self.snapshot_store.create(artifacts)

    def restore_snapshot(self, snapshot_id: str) -> Snapshot:
        return self.snapshot_store.restore(snapshot_id)


_repo = ProspectRepository()
_snapshot_store = SnapshotStore()
_service = ProspectService(_repo, _snapshot_store)

app = FastAPI(title="Prospect Discovery Service", version="1.0.0")


def get_service() -> ProspectService:
    return _service


@app.post("/discover")
async def discover(request: ProspectRequest, service: ProspectService = Depends(get_service)) -> List[dict[str, str]]:
    prospects = service.discover(request.query, request.limit)
    return [
        {
            "organization": prospect.organization,
            "website": prospect.website,
            "score": prospect.score,
            "provenance_key": prospect.provenance_key,
        }
        for prospect in prospects
    ]


@app.post("/snapshots")
async def create_snapshot(request: SnapshotRequest, service: ProspectService = Depends(get_service)) -> dict[str, str]:
    snapshot = service.create_snapshot(request.artifacts)
    return {"snapshot_id": snapshot.snapshot_id, "stored_at": snapshot.stored_at.isoformat()}


@app.post("/snapshots/{snapshot_id}/restore")
async def restore_snapshot(snapshot_id: str, service: ProspectService = Depends(get_service)) -> dict[str, str]:
    snapshot = service.restore_snapshot(snapshot_id)
    return {"snapshot_id": snapshot.snapshot_id, "artifact_count": str(len(snapshot.artifacts))}
