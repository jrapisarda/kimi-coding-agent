"""End-to-end tests covering API gateway orchestrations."""
from __future__ import annotations

from fastapi.testclient import TestClient

from codex_chopan_app.services.api_gateway.main import app

client = TestClient(app)
API_KEY = {"X-API-Key": "test-key"}


def test_healthcheck() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_create_content_draft() -> None:
    payload = {"brief": "Highlight donor impact", "language": "en"}
    response = client.post("/api/content/draft", json=payload, headers=API_KEY)
    assert response.status_code == 200
    body = response.json()
    assert body["language"] == "en"
    assert "draft_id" in body


def test_email_campaign_and_webhook() -> None:
    payload = {
        "subject": "Giving Tuesday",
        "audience_segment": ["a@example.com", "b@example.com"],
        "body": "Join our mission",
        "suppression_list": ["b@example.com"],
    }
    response = client.post("/api/email/campaign", json=payload, headers=API_KEY)
    assert response.status_code == 200
    body = response.json()
    assert body["suppressed"] == ["b@example.com"]

    webhook_payload = {
        "events": [
            {"provider": "sendgrid", "event": "delivered", "recipient": "a@example.com", "ts": "2024-01-01T00:00:00"}
        ]
    }
    webhook_response = client.post("/api/email/webhooks", json=webhook_payload, headers=API_KEY)
    assert webhook_response.status_code == 200
    assert webhook_response.json()[0]["event"] == "delivered"


def test_social_schedule_and_metrics() -> None:
    payload = {"network": "linkedin", "message": "Impact story"}
    response = client.post("/api/social/schedule", json=payload, headers=API_KEY)
    assert response.status_code == 200
    post_id = response.json()["post_id"]

    metrics = client.get("/api/social/metrics/linkedin", headers=API_KEY)
    assert metrics.status_code == 200
    assert any(item["post_id"] == post_id for item in metrics.json())


def test_prospect_discovery() -> None:
    response = client.post(
        "/api/prospect/discover",
        json={"query": "Chopan donors", "limit": 2},
        headers=API_KEY,
    )
    assert response.status_code == 200
    prospects = response.json()
    assert len(prospects) == 2
    assert all("provenance_key" in item for item in prospects)


def test_snapshot_create_and_restore() -> None:
    artifacts = [{"name": "Artifact", "url": "https://chopan.example.org/doc"}]
    create_response = client.post("/api/snapshots", json=artifacts, headers=API_KEY)
    assert create_response.status_code == 200
    snapshot_id = create_response.json()["snapshot_id"]

    restore_response = client.post(
        "/api/snapshots/restore", json={"target_id": snapshot_id}, headers=API_KEY
    )
    assert restore_response.status_code == 200
    assert restore_response.json()["restored"] is True


def test_worker_task_trigger() -> None:
    response = client.post(
        "/api/tasks/content", params={"brief": "async draft"}, headers=API_KEY
    )
    assert response.status_code == 200
    assert response.json()["draft"] == "ASYNC DRAFT"
