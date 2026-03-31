from __future__ import annotations

from sqlalchemy import create_engine, text


def test_db_connection_after_migration(migrated_database_url: str) -> None:
    engine = create_engine(migrated_database_url)
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1")).scalar_one()
    assert result == 1
