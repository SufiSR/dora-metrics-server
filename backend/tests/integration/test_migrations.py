from __future__ import annotations

import pytest
from sqlalchemy import create_engine, text

pytestmark = pytest.mark.integration

# Core tables that must exist after Alembic upgrade head (all domain models)
_EXPECTED_TABLES = frozenset(
    {
        "alembic_version",
        "app_configuration",
        "repository",
        "merge_request",
        "release",
        "sync_log",
        "metric_snapshot",
        "production_bug",
        "bug_release",
        "issue_worklog",
    }
)


def test_db_connection_and_schema_after_migration(migrated_database_url: str) -> None:
    engine = create_engine(migrated_database_url)
    with engine.connect() as connection:
        one = connection.execute(text("SELECT 1")).scalar_one()
        assert one == 1

        version = connection.execute(
            text("SELECT version_num FROM alembic_version LIMIT 1")
        ).scalar_one()
        assert isinstance(version, str) and version.strip() != ""

        rows = connection.execute(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
            )
        ).fetchall()
        present = {r[0] for r in rows}
        assert _EXPECTED_TABLES.issubset(present), (
            f"Missing tables: {sorted(_EXPECTED_TABLES - present)}"
        )
