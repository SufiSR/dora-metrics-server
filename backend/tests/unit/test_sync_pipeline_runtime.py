"""Unit tests for sync_pipeline runtime / phase transition helpers."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.models import Base
from app.models.sync_log import SyncLog
from app.services import sync_pipeline as sp


def _session_maker() -> sessionmaker[Session]:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)

    @event.listens_for(engine, "connect")
    def _fk(dbapi_conn, _rec):  # type: ignore[no-untyped-def]
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, class_=Session, autoflush=False, autocommit=False)


def test_new_pipeline_runtime_shape() -> None:
    r = sp._new_pipeline_runtime(trigger="manual")
    assert r["current_phase"] == "queued"
    assert set(r["phases"]) == set(sp.PIPELINE_PHASES)
    assert r["phases"]["gitlab"]["status"] == "pending"


def test_transition_runtime_phase_running_to_success() -> None:
    rt = sp._new_pipeline_runtime(trigger="nightly")
    sp._transition_runtime_phase(
        rt, current_phase="gitlab", phase="gitlab", status="running"
    )
    assert rt["phases"]["gitlab"]["started_at"]
    sp._transition_runtime_phase(
        rt,
        current_phase="complete",
        phase="gitlab",
        status="success",
        records_processed={"repositories": 1},
    )
    assert rt["phases"]["gitlab"]["status"] == "success"
    assert rt["phases"]["gitlab"]["duration_seconds"] is not None
    assert rt["phases"]["gitlab"]["records_processed"] == {"repositories": 1}


def test_transition_runtime_phase_duration_parse_failure() -> None:
    rt = sp._new_pipeline_runtime(trigger="x")
    rt["phases"]["gitlab"]["started_at"] = "2026-13-40T00:00:00+00:00"  # invalid date
    sp._transition_runtime_phase(
        rt, current_phase="c", phase="gitlab", status="success"
    )
    assert rt["phases"]["gitlab"]["duration_seconds"] is None


def test_transition_skipped_with_no_start_sets_start() -> None:
    rt = sp._new_pipeline_runtime(trigger="x")
    sp._transition_runtime_phase(
        rt, current_phase="c", phase="jira", status="skipped"
    )
    assert rt["phases"]["jira"]["status"] == "skipped"
    assert rt["phases"]["jira"]["started_at"] and rt["phases"]["jira"]["finished_at"]


def test_append_runtime_error_truncates() -> None:
    rt: dict = {"errors": []}
    sp._append_runtime_error(rt, "e" * 500)
    assert len(rt["errors"][-1]) == 400


def test_transition_message_truncates() -> None:
    rt = sp._new_pipeline_runtime(trigger="x")
    sp._transition_runtime_phase(
        rt,
        current_phase="a",
        phase="gitlab",
        status="failed",
        message="m" * 500,
    )
    assert len(rt["phases"]["gitlab"]["message"] or "") <= 400


def test_sync_normalize_version_key() -> None:
    assert "1.0.0" in sp._normalize_version_key("V1.0.0")
    assert sp._normalize_version_key("   ") == set()


def test_create_and_finish_nightly_sync_log_round_trip() -> None:
    maker = _session_maker()
    log_id = sp._create_nightly_sync_log(maker, trigger="unit")
    assert log_id >= 1
    sp._finish_nightly_sync_log(
        maker,
        log_id=log_id,
        status="failed",
        records_processed=0,
        error_message="unit",
        details_json={"z": 1},
    )
    with maker() as db:
        row = db.get(SyncLog, log_id)
        assert row is not None
        assert row.status == "failed"
        assert row.error_message == "unit"


def test_update_nightly_sync_log_details_merges_json() -> None:
    maker = _session_maker()
    t = datetime.now(timezone.utc)
    with maker() as db:
        db.add(
            SyncLog(
                id=1,
                source="nightly",
                started_at=t,
                status="running",
                details_json={"a": 1, "phase": 1},
            )
        )
        db.commit()

    def factory() -> Session:
        return maker()

    sp._update_nightly_sync_log_details(factory, log_id=1, details_json={"b": 2, "a": 2})
    with maker() as db2:
        row = db2.get(SyncLog, 1)
        assert row is not None
        assert row.details_json == {"a": 2, "phase": 1, "b": 2}
