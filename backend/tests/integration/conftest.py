from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from testcontainers.postgres import PostgresContainer

from alembic import command

# conftest lives at backend/tests/integration/ — backend root is two levels up
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent


def _docker_daemon_reachable() -> bool:
    try:
        import docker

        docker.from_env().ping()
        return True
    except Exception:
        return False


@pytest.fixture(scope="session")
def postgres_url() -> Generator[str, None, None]:
    if not _docker_daemon_reachable():
        pytest.skip(
            "Docker daemon not reachable; integration tests need Docker for PostgreSQL.",
        )
    with PostgresContainer("postgres:16") as postgres:
        yield postgres.get_connection_url()


@pytest.fixture(scope="session")
def migrated_database_url(postgres_url: str) -> str:
    alembic_cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    alembic_cfg.set_main_option("sqlalchemy.url", postgres_url)
    command.upgrade(alembic_cfg, "head")
    return postgres_url


def _psycopg_url(url: str) -> str:
    if url.startswith("postgresql://") and "+psycopg2" not in url:
        return url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url


@pytest.fixture
def api_client(migrated_database_url: str, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Full FastAPI app against migrated Postgres; no external GitLab/Jira tokens."""
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


@pytest.fixture
def session_factory(migrated_database_url: str) -> sessionmaker[Session]:
    """SQLAlchemy session factory against the same migrated DB as the API tests."""
    engine = create_engine(_psycopg_url(migrated_database_url), future=True)
    return sessionmaker(
        bind=engine,
        class_=Session,
        autoflush=False,
        autocommit=False,
    )
