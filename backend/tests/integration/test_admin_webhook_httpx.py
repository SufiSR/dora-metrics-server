from __future__ import annotations

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration

_WEBHOOK_URL = "https://integration-hooks.example.test/notify"


@respx.mock
def test_admin_webhook_test_delivers_to_url(api_client: TestClient) -> None:
    route = respx.post(_WEBHOOK_URL).mock(return_value=httpx.Response(200, text="ok"))

    assert api_client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "adminpass"},
    ).status_code == 200

    r = api_client.post(
        "/api/admin/config/webhook/test",
        json={"webhook_url": _WEBHOOK_URL},
    )
    assert r.status_code == 200
    b = r.json()
    assert b["delivered"] is True
    assert b["effective_webhook_url"].startswith("https://integration-hooks")
    assert b["payload"]["event"] == "SYNC_TEST"
    assert route.call_count == 1
