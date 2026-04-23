from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


def test_metrics_current_shape(api_client: TestClient) -> None:
    r = api_client.get("/api/metrics/current")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body["repository_count"], int)
    assert body["repository_count"] >= 0
    assert "period_start" in body and "period_end" in body
    assert "generated_at" in body


def test_repositories_list_matches_total(api_client: TestClient) -> None:
    r = api_client.get("/api/repositories")
    assert r.status_code == 200
    b = r.json()
    assert isinstance(b["total"], int)
    assert len(b["repositories"]) == b["total"]


def test_metrics_history_default_window(api_client: TestClient) -> None:
    r = api_client.get("/api/metrics/history")
    assert r.status_code == 200
    b = r.json()
    assert b["period_type"] == "WEEK"
    assert "from" in b and "to" in b
    assert b["pagination"]["page"] == 0


def test_sync_status_shape(api_client: TestClient) -> None:
    r = api_client.get("/api/sync/status")
    assert r.status_code == 200
    b = r.json()
    assert "last_sync" in b
    assert "sync_schedule_cron" in b


def test_mttr_alpha_summary_empty(api_client: TestClient) -> None:
    r = api_client.get("/api/metrics/bugs/mttr-alpha/summary")
    assert r.status_code == 200
    b = r.json()
    assert b["period_type"] == "WEEK"
    assert b["incident_count"] == 0


def test_legacy_health_root(api_client: TestClient) -> None:
    r = api_client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_admin_data_health_requires_session(api_client: TestClient) -> None:
    r = api_client.get("/api/admin/data-health")
    assert r.status_code == 401
