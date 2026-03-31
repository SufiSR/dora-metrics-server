from __future__ import annotations

from collections.abc import Generator

import pytest
from alembic.config import Config
from testcontainers.postgres import PostgresContainer

from alembic import command


@pytest.fixture(scope="session")
def postgres_url() -> Generator[str, None, None]:
    with PostgresContainer("postgres:16") as postgres:
        yield postgres.get_connection_url()


@pytest.fixture(scope="session")
def migrated_database_url(postgres_url: str) -> str:
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", postgres_url)
    command.upgrade(alembic_cfg, "head")
    return postgres_url
