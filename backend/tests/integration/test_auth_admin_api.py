from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


def _docker_available() -> bool:
    try:
        import docker

        docker.from_env().ping()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _docker_available(), reason="Docker is not available")


def _psycopg_url(url: str) -> str:
    if url.startswith("postgresql://") and "+psycopg2" not in url:
        return url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url


@pytest.fixture
def api_client(migrated_database_url: str, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("DATABASE_URL", _psycopg_url(migrated_database_url))
    monkeypatch.setenv("DORA_SESSION_SECRET", "integration-test-session-secret-32c")
    monkeypatch.setenv("DORA_ADMIN_USERNAME", "admin")
    monkeypatch.setenv("DORA_ADMIN_PASSWORD", "adminpass")
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

    import app.database as db_mod

    db_mod._engine = None

    from app.main import app

    with TestClient(app) as client:
        yield client


def test_api_health_reports_database_up(api_client: TestClient) -> None:
    response = api_client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "UP"
    assert body["components"]["database"]["status"] == "UP"


def test_auth_me_anonymous(api_client: TestClient) -> None:
    response = api_client.get("/api/auth/me")
    assert response.status_code == 200
    assert response.json() == {"role": None, "username": None}


def test_admin_config_requires_session(api_client: TestClient) -> None:
    response = api_client.get("/api/admin/config")
    assert response.status_code == 401
    err = response.json()
    assert err["error"] == "UNAUTHORIZED"


def test_login_invalid_credentials(api_client: TestClient) -> None:
    response = api_client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "wrong"},
    )
    assert response.status_code == 401
    assert response.json()["error"] == "UNAUTHORIZED"


def test_login_session_allows_admin_config_and_logout(api_client: TestClient) -> None:
    login = api_client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "adminpass"},
    )
    assert login.status_code == 200
    assert login.json()["role"] == "admin"

    me = api_client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["role"] == "admin"
    assert me.json()["username"] == "admin"

    config = api_client.get("/api/admin/config")
    assert config.status_code == 200
    cfg = config.json()
    assert cfg["gitlab_url"]
    assert cfg["gitlab_token_hint"] is None or "*" in str(cfg["gitlab_token_hint"])

    out = api_client.post("/api/auth/logout")
    assert out.status_code == 204

    blocked = api_client.get("/api/admin/config")
    assert blocked.status_code == 401


def test_patch_admin_config_gitlab_url(api_client: TestClient) -> None:
    api_client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "adminpass"},
    )
    response = api_client.patch(
        "/api/admin/config",
        json={"gitlab_url": "https://patched-gitlab.example"},
    )
    assert response.status_code == 200
    assert response.json()["gitlab_url"] == "https://patched-gitlab.example"
