from __future__ import annotations

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models.sync_log import SyncLog
from app.schemas.health import ComponentHealth, HealthResponse


def build_health_response(db: Session) -> HealthResponse:
    db_ok = False
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    gitlab_at = db.scalar(
        select(SyncLog.finished_at)
        .where(
            SyncLog.source == "gitlab",
            SyncLog.status == "success",
            SyncLog.finished_at.isnot(None),
        )
        .order_by(SyncLog.finished_at.desc())
        .limit(1)
    )
    jira_at = db.scalar(
        select(SyncLog.finished_at)
        .where(
            SyncLog.source == "jira",
            SyncLog.status == "success",
            SyncLog.finished_at.isnot(None),
        )
        .order_by(SyncLog.finished_at.desc())
        .limit(1)
    )

    gitlab_component = ComponentHealth(
        status="UP" if gitlab_at is not None else "DOWN",
        last_successful_connection=gitlab_at,
    )
    jira_component = ComponentHealth(
        status="UP" if jira_at is not None else "DOWN",
        last_successful_connection=jira_at,
    )
    database_component = ComponentHealth(status="UP" if db_ok else "DOWN")

    overall = "UP" if db_ok else "DOWN"

    return HealthResponse(
        status=overall,
        components={
            "database": database_component,
            "gitlab": gitlab_component,
            "jira": jira_component,
        },
    )
