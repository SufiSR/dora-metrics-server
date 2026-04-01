"""sync_log.details_json for nightly sync API payload."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260402_0006"
down_revision = "20260401_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sync_log", sa.Column("details_json", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("sync_log", "details_json")
