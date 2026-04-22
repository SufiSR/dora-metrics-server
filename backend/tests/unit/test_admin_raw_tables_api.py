from __future__ import annotations

from collections.abc import Generator
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

import app.database as database
from app.api.deps import get_db
from app.models import Base
from app.models.issue_worklog import IssueWorklog
from app.models.merge_request import MergeRequest
from app.models.production_bug import ProductionBug
from app.models.release import Release
from app.models.repository import Repository
from app.models.sync_log import SyncLog


@pytest.fixture
def raw_tables_client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Generator[TestClient, None, None]:
    db_path = tmp_path / "admin_raw_tables.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+pysqlite:///{db_path.resolve().as_posix()}")
    monkeypatch.setenv("DORA_SESSION_SECRET", "unit-test-session-secret-strings")
    monkeypatch.setenv("DORA_ADMIN_USERNAME", "admin")
    monkeypatch.setenv("DORA_ADMIN_PASSWORD", "secret")
    monkeypatch.setenv("CONFIG_ENCRYPTION_KEY", "devops-438-key")
    monkeypatch.setenv("GITLAB_BASE_URL", "https://gitlab.example.com")
    monkeypatch.setenv("GITLAB_API_TOKEN", "token")
    monkeypatch.setenv("JIRA_BASE_URL", "https://plunet.atlassian.net")
    monkeypatch.setenv("JIRA_USER_EMAIL", "devops@example.com")
    monkeypatch.setenv("JIRA_API_TOKEN", "jira-token")

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


def _utc(year: int, month: int, day: int) -> datetime:
    return datetime(year, month, day, tzinfo=timezone.utc)


def test_admin_raw_tables_requires_admin_session(raw_tables_client: TestClient) -> None:
    response = raw_tables_client.get("/api/admin/raw-tables/repository")
    assert response.status_code == 401
    assert response.json()["error"] == "UNAUTHORIZED"


def test_admin_raw_tables_support_search_sort_and_joined_values(
    raw_tables_client: TestClient,
) -> None:
    with Session(database.get_engine()) as db:
        db.add(
            Repository(
                id=1,
                gitlab_id=111,
                name="Platform",
                path="group/platform",
                default_branch="main",
                active=True,
            )
        )
        db.add(
            Repository(
                id=2,
                gitlab_id=222,
                name="Payments",
                path="group/payments",
                default_branch="main",
                active=True,
            )
        )
        db.add(
            Release(
                id=1,
                repository_id=1,
                tag_name="v1.0.0",
                customer_release=True,
                version_major=1,
                version_minor=0,
                version_patch=0,
                commit_sha="a" * 40,
                committed_at=_utc(2026, 4, 1),
            )
        )
        db.add(
            ProductionBug(
                id=1,
                jira_key="DEVOPS-100",
                summary="Payment bug",
                healthy=False,
                jira_created_at_valid=True,
                created_at=_utc(2026, 4, 3),
            )
        )
        db.add(
            IssueWorklog(
                id=1,
                bug_id=1,
                jira_worklog_id="w-1",
                author="Alice",
                started=_utc(2026, 4, 4),
                time_spent_seconds=3600,
            )
        )
        db.add(
            MergeRequest(
                id=1,
                repository_id=1,
                gitlab_mr_id=123,
                title="Fix: reliability improvements",
                author="Bob",
                target_branch="main",
                created_at=_utc(2026, 4, 2),
                merged_at=_utc(2026, 4, 5),
            )
        )
        db.add(
            SyncLog(
                id=1,
                source="gitlab",
                started_at=_utc(2026, 4, 5),
                finished_at=_utc(2026, 4, 5),
                status="success",
                records_processed=42,
            )
        )
        db.commit()

    login = raw_tables_client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "secret"},
    )
    assert login.status_code == 200

    response = raw_tables_client.get(
        "/api/admin/raw-tables/release",
        params={"search": "group/platform", "sort_by": "repository", "sort_dir": "asc"},
    )
    assert response.status_code == 200
    release_rows = response.json()["rows"]
    assert len(release_rows) == 1
    assert release_rows[0]["repository"] == "group/platform"

    response = raw_tables_client.get(
        "/api/admin/raw-tables/issue_worklog",
        params={"search": "DEVOPS-100", "sort_by": "bug_jira_key", "sort_dir": "asc"},
    )
    assert response.status_code == 200
    worklog_body = response.json()
    assert worklog_body["rows"][0]["bug_jira_key"] == "DEVOPS-100"
    assert worklog_body["pagination"]["total_elements"] == 1


def test_admin_raw_tables_unknown_table_returns_not_found(raw_tables_client: TestClient) -> None:
    login = raw_tables_client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "secret"},
    )
    assert login.status_code == 200
    response = raw_tables_client.get("/api/admin/raw-tables/not-a-table")
    assert response.status_code == 404
