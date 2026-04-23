from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


def test_metrics_repository_not_found_returns_404(api_client: TestClient) -> None:
    r = api_client.get("/api/metrics/repository/999999")
    assert r.status_code == 404
    body = r.json()
    assert "error" in body or "detail" in body


def test_metrics_history_invalid_period_type_rejected(api_client: TestClient) -> None:
    r = api_client.get("/api/metrics/history", params={"period_type": "NOT_A_PERIOD"})
    # FastAPI may surface invalid enum as 422; error handler may normalize to 400.
    assert r.status_code in (400, 422)


def test_metrics_history_rejects_inverted_date_range(api_client: TestClient) -> None:
    r = api_client.get(
        "/api/metrics/history",
        params={"from": "2026-12-01", "to": "2026-01-01"},
    )
    assert r.status_code == 400
    err = r.json()
    assert err.get("error") in ("BAD_REQUEST", None) or "detail" in err


def test_admin_raw_table_unknown_name_returns_404(api_client: TestClient) -> None:
    assert api_client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "adminpass"},
    ).status_code == 200
    r = api_client.get("/api/admin/raw-tables/not_a_real_table_name")
    assert r.status_code == 404


def test_data_health_authorized_returns_payload(api_client: TestClient) -> None:
    assert api_client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "adminpass"},
    ).status_code == 200
    r = api_client.get("/api/admin/data-health")
    assert r.status_code == 200
    b = r.json()
    assert "summary" in b
    assert "generated_at" in b


def test_mttr_alpha_releases_list_empty(api_client: TestClient) -> None:
    r = api_client.get("/api/metrics/bugs/mttr-alpha/releases")
    assert r.status_code == 200
    b = r.json()
    assert b["period_type"] == "WEEK"
    assert b["pagination"]["total_elements"] == 0


def test_manual_sync_trigger_accepts_with_session(api_client: TestClient) -> None:
    assert api_client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "adminpass"},
    ).status_code == 200
    r = api_client.post("/api/admin/sync/trigger")
    assert r.status_code == 202
    assert r.json().get("detail") == "Sync triggered"
