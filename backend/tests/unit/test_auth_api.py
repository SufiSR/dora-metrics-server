from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

import app.database as database
from app.api.deps import get_db
from app.models import Base


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
    db_path = tmp_path / "auth_api.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+pysqlite:///{db_path.resolve().as_posix()}")
    monkeypatch.setenv("DORA_SESSION_SECRET", "unit-test-session-secret-strings")
    monkeypatch.setenv("DORA_ADMIN_USERNAME", "admin")
    monkeypatch.setenv("DORA_ADMIN_PASSWORD", "secret")
    monkeypatch.setenv("CONFIG_ENCRYPTION_KEY", "devops-438-key")
    for key in (
        "GITLAB_BASE_URL",
        "GITLAB_TOKEN",
        "GITLAB_API_TOKEN",
        "JIRA_BASE_URL",
        "JIRA_API_TOKEN",
        "JIRA_USER_EMAIL",
    ):
        monkeypatch.delenv(key, raising=False)

    database._engine = None
    Base.metadata.create_all(database.get_engine())
    maker = sessionmaker(
        bind=database.get_engine(),
        class_=Session,
        autoflush=False,
        autocommit=False,
    )

    def _db() -> Generator[Session, None, None]:
        db = maker()
        try:
            yield db
        finally:
            db.close()

    from app.main import app

    app.dependency_overrides[get_db] = _db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_me_anonymous(client: TestClient) -> None:
    response = client.get("/api/auth/me")
    assert response.status_code == 200
    assert response.json() == {"role": None, "username": None}


def test_admin_config_unauthorized(client: TestClient) -> None:
    response = client.get("/api/admin/config")
    assert response.status_code == 401
    assert response.json()["error"] == "UNAUTHORIZED"


def test_login_and_session_cookie_flow(client: TestClient) -> None:
    bad = client.post("/api/auth/login", json={"username": "admin", "password": "nope"})
    assert bad.status_code == 401

    ok = client.post("/api/auth/login", json={"username": "admin", "password": "secret"})
    assert ok.status_code == 200
    assert ok.json()["role"] == "admin"

    cfg = client.get("/api/admin/config")
    assert cfg.status_code == 200
    body = cfg.json()
    assert body["gitlab_url"]

    logout = client.post("/api/auth/logout")
    assert logout.status_code == 204

    again = client.get("/api/admin/config")
    assert again.status_code == 401


def test_patch_admin_config_after_login(client: TestClient) -> None:
    client.post("/api/auth/login", json={"username": "admin", "password": "secret"})
    response = client.patch(
        "/api/admin/config",
        json={"gitlab_url": "https://patched.example"},
    )
    assert response.status_code == 200
    assert response.json()["gitlab_url"] == "https://patched.example"


def test_webhook_test_endpoint_requires_session(client: TestClient) -> None:
    response = client.post("/api/admin/config/webhook/test", json={})
    assert response.status_code == 401


def test_webhook_test_endpoint_uses_draft_url(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    client.post("/api/auth/login", json={"username": "admin", "password": "secret"})
    captured: dict[str, object] = {}

    def fake_send(url: str | None, payload: dict[str, object], **_kwargs: object) -> bool:
        captured["url"] = url
        captured["payload"] = payload
        return True

    import app.api.admin_config as admin_config_api

    monkeypatch.setattr(admin_config_api, "send_webhook_notification", fake_send)
    response = client.post(
        "/api/admin/config/webhook/test",
        json={"webhook_url": "https://hooks.example.test/abc"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["delivered"] is True
    assert body["effective_webhook_url"] == "https://hooks.example.test/abc"
    assert body["payload"]["event"] == "SYNC_TEST"
    assert captured["url"] == "https://hooks.example.test/abc"


def test_webhook_test_endpoint_falls_back_to_saved_url(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    client.post("/api/auth/login", json={"username": "admin", "password": "secret"})
    client.patch(
        "/api/admin/config",
        json={"notifications_webhook_url": "https://hooks.example.test/saved"},
    )

    captured: dict[str, object] = {}

    def fake_send(url: str | None, payload: dict[str, object], **_kwargs: object) -> bool:
        captured["url"] = url
        captured["payload"] = payload
        return True

    import app.api.admin_config as admin_config_api

    monkeypatch.setattr(admin_config_api, "send_webhook_notification", fake_send)
    response = client.post("/api/admin/config/webhook/test", json={})
    assert response.status_code == 200
    assert response.json()["effective_webhook_url"] == "https://hooks.example.test/saved"
    assert captured["url"] == "https://hooks.example.test/saved"


def test_webhook_test_endpoint_missing_url_returns_400(client: TestClient) -> None:
    client.post("/api/auth/login", json={"username": "admin", "password": "secret"})
    response = client.post("/api/admin/config/webhook/test", json={})
    assert response.status_code == 400


def test_login_request_validation_error_returns_bad_request_envelope(client: TestClient) -> None:
    r = client.post("/api/auth/login", json={"username": "admin"})
    assert r.status_code == 400
    assert r.json().get("error") == "BAD_REQUEST"


def test_login_rejects_when_env_password_unset(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DORA_ADMIN_PASSWORD", "")
    r = client.post("/api/auth/login", json={"username": "admin", "password": "x"})
    assert r.status_code == 401
