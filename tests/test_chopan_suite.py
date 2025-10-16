"""Executes the Chopan outreach microservice test harness."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from codex_chopan_app.tests.api import test_gateway
from codex_chopan_app.tests.content import test_content_service
from codex_chopan_app.tests.email import test_email_service
from codex_chopan_app.tests.social import test_social_service
from codex_chopan_app.tests.prospect import test_prospect_service
from codex_chopan_app.tests.worker import test_tasks


def test_gateway_healthcheck() -> None:
    test_gateway.test_healthcheck()


def test_gateway_content_draft() -> None:
    test_gateway.test_create_content_draft()


def test_gateway_email_flow() -> None:
    test_gateway.test_email_campaign_and_webhook()


def test_gateway_social_flow() -> None:
    test_gateway.test_social_schedule_and_metrics()


def test_gateway_prospect_flow() -> None:
    test_gateway.test_prospect_discovery()


def test_gateway_snapshot_flow() -> None:
    test_gateway.test_snapshot_create_and_restore()


def test_gateway_worker_trigger() -> None:
    test_gateway.test_worker_task_trigger()


def test_content_service_logic() -> None:
    test_content_service.test_generate_and_translate()


def test_email_service_suppression() -> None:
    test_email_service.test_campaign_suppression()


def test_social_service_publication() -> None:
    test_social_service.test_schedule_publishes_when_past()


def test_prospect_service_discovery() -> None:
    test_prospect_service.test_discover_returns_scored_prospects()


def test_prospect_service_compliance(monkeypatch) -> None:
    test_prospect_service.test_discover_rejects_disallowed_domain(monkeypatch)


def test_worker_tasks() -> None:
    test_tasks.test_generate_content_task()
    test_tasks.test_prospect_score_task()
