"""Direct unit tests for release_drilldown_service helpers and DB queries."""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

import app.services.release_drilldown_service as rds
from app.config_schema import ConfigurationSchema
from app.models import Base
from app.models.merge_request import MergeRequest
from app.models.production_bug import ProductionBug
from app.models.release import Release
from app.models.repository import Repository


def _session_maker() -> sessionmaker[Session]:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)

    @event.listens_for(engine, "connect")
    def _fk(dbapi_conn, _rec):  # type: ignore[no-untyped-def]
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, class_=Session, autoflush=False, autocommit=False)


def _utc(*args: int) -> datetime:
    return datetime(*args, tzinfo=timezone.utc)


def test_lane_from_version() -> None:
    assert rds._lane(1, 0, 0) == "major"
    assert rds._lane(1, 1, 0) == "minor"
    assert rds._lane(1, 0, 1) == "patch"
    assert rds._lane(1, None, 0) == "unknown"


def test_build_gitlab_compare_url_strips_slashes() -> None:
    u = rds.build_gitlab_compare_url(
        base_url="https://gitlab.test/",
        project_path="  /a/b/  ",
        from_tag="A",
        to_tag="B",
    )
    assert u == "https://gitlab.test/a/b/-/compare/A...B"


def test_get_customer_release_rejects_inactive_repo() -> None:
    maker = _session_maker()
    t = _utc(2026, 4, 1, 12, 0)
    with maker() as db:
        db.add(
            Repository(
                id=1,
                gitlab_id=1,
                name="r",
                path="g/r",
                default_branch="main",
                active=False,
            )
        )
        db.flush()
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
                committed_at=t,
            )
        )
        db.commit()
        assert rds.get_customer_release_or_none(db, repository_id=1, tag_name="v1.0.0") is None


def test_find_previous_and_mr_counts() -> None:
    maker = _session_maker()
    t1 = _utc(2026, 4, 1, 12, 0)
    t0 = _utc(2026, 3, 1, 12, 0)
    with maker() as db:
        db.add(
            Repository(
                id=1,
                gitlab_id=1,
                name="r",
                path="g/r",
                default_branch="main",
                active=True,
            )
        )
        db.flush()
        for rid, tag, c_at in ((1, "v1.0.0", t0), (2, "v1.1.0", t1)):
            db.add(
                Release(
                    id=rid,
                    repository_id=1,
                    tag_name=tag,
                    customer_release=True,
                    version_major=1,
                    version_minor=0,
                    version_patch=rid - 1,
                    commit_sha="b" * 40,
                    committed_at=c_at,
                )
            )
        db.flush()
        for mid, mrid, jk in ((1, 10, "X-1"), (2, 11, "X-2"), (3, 12, None)):
            db.add(
                MergeRequest(
                    id=mid,
                    repository_id=1,
                    gitlab_mr_id=mrid,
                    target_branch="main",
                    created_at=t0,
                    merged_at=t0,
                    first_customer_tag="v1.1.0",
                    first_customer_tag_date=t1,
                    lead_time_hours=None,
                    jira_key=jk,
                )
            )
        db.commit()
        prev = rds.find_previous_customer_release(db, repository_id=1, committed_at=t1)
        assert prev is not None
        assert prev.tag_name == "v1.0.0"
        assert rds.count_merge_requests_for_release(db, repository_id=1, tag_name="v1.1.0") == 3
        assert rds.count_merge_requests_with_jira_key(db, repository_id=1, tag_name="v1.1.0") == 2


def test_list_merge_requests_includes_cohort_flag() -> None:
    maker = _session_maker()
    t = _utc(2026, 4, 1, 12, 0)
    with maker() as db:
        db.add(
            Repository(
                id=1,
                gitlab_id=1,
                name="r",
                path="g/r",
                default_branch="main",
                active=True,
            )
        )
        db.flush()
        db.add(
            Release(
                id=1,
                repository_id=1,
                tag_name="v1.0.0",
                customer_release=True,
                version_major=1,
                version_minor=0,
                version_patch=0,
                commit_sha="c" * 40,
                committed_at=t,
            )
        )
        db.add(
            MergeRequest(
                id=1,
                repository_id=1,
                gitlab_mr_id=99,
                title="bump  release",  # excluded by default release title marker
                target_branch="main",
                source_branch="dev",
                created_at=t,
                merged_at=t,
                first_customer_tag="v1.0.0",
                first_customer_tag_date=t,
                lead_time_hours=None,
            )
        )
        db.commit()
        rows = rds.list_merge_requests_for_release_page(
            db,
            repository_id=1,
            tag_name="v1.0.0",
            page=0,
            size=5,
            config=ConfigurationSchema(),
        )
        assert len(rows) == 1
        assert rows[0].included_in_lead_time_metrics is False


def test_count_customer_releases_filters_by_repo() -> None:
    maker = _session_maker()
    t = _utc(2026, 4, 1, 12, 0)
    with maker() as db:
        for rid in (1, 2):
            db.add(
                Repository(
                    id=rid,
                    gitlab_id=rid,
                    name=f"r{rid}",
                    path=f"g/r{rid}",
                    default_branch="main",
                    active=True,
                )
            )
        db.flush()
        for rid, tid in ((1, 1), (1, 2), (2, 3)):
            db.add(
                Release(
                    id=tid,
                    repository_id=rid,
                    tag_name=f"v{rid}.{tid}.0",
                    customer_release=True,
                    version_major=1,
                    version_minor=0,
                    version_patch=0,
                    commit_sha="d" * 40,
                    committed_at=t,
                )
            )
        db.commit()
        assert rds.count_customer_releases(db, repository_id=None) == 3
        assert rds.count_customer_releases(db, repository_id=1) == 2


def test_latest_mttr_alpha_incident_window_branches() -> None:
    with _session_maker()() as db0:
        assert rds.latest_mttr_alpha_incident_window(db0, period_type="QUARTER") is None

    maker = _session_maker()
    t = _utc(2026, 4, 16, 12, 0)  # Thursday, week starting Monday 2026-04-13
    with maker() as db:
        db.add(
            Repository(
                id=1,
                gitlab_id=1,
                name="r",
                path="g/r",
                default_branch="main",
                active=True,
            )
        )
        db.flush()
        db.add(
            Release(
                id=1,
                repository_id=1,
                tag_name="v1",
                customer_release=True,
                version_major=1,
                version_minor=0,
                version_patch=0,
                commit_sha="e" * 40,
                committed_at=t,
            )
        )
        db.commit()
        wk = rds.latest_mttr_alpha_incident_window(db, period_type="WEEK")
        assert wk is not None
        assert wk.period_start.date() == date(2026, 4, 13)  # Monday of week of 2026-04-16
        mon = rds.latest_mttr_alpha_incident_window(db, period_type="month")
        assert mon is not None
        assert mon.period_start.date() == date(2026, 4, 1)
    with _session_maker()() as db3:
        db3.add(
            Repository(
                id=1,
                gitlab_id=1,
                name="r",
                path="g/r",
                default_branch="main",
                active=True,
            )
        )
        db3.flush()
        db3.add(
            Release(
                id=1,
                repository_id=1,
                tag_name="q",
                customer_release=True,
                version_major=1,
                version_minor=0,
                version_patch=0,
                commit_sha="f" * 40,
                committed_at=_utc(2026, 5, 2, 12, 0),  # Q2 start -> quarter Apr–Jun
            )
        )
        db3.commit()
        qu = rds.latest_mttr_alpha_incident_window(db3, period_type="quarter")
        assert qu is not None
        assert qu.period_start.date() == date(2026, 4, 1)
        # period_end is exclusive [start, end) upper bound, aligned to quarter calendar
        assert qu.period_end.date() == date(2026, 7, 1)
    with _session_maker()() as db4:
        db4.add(
            Repository(
                id=1,
                gitlab_id=1,
                name="r",
                path="g/r",
                default_branch="main",
                active=True,
            )
        )
        db4.flush()
        db4.add(
            Release(
                id=1,
                repository_id=1,
                tag_name="t",
                customer_release=True,
                version_major=1,
                version_minor=0,
                version_patch=0,
                commit_sha="g" * 40,
                committed_at=_utc(2026, 1, 1, 12, 0),
            )
        )
        db4.commit()
        with pytest.raises(ValueError, match="Unsupported period type"):
            rds.latest_mttr_alpha_incident_window(db4, period_type="DAY")


def test_median_and_list_mttr_helpers() -> None:
    maker = _session_maker()
    t0 = _utc(2026, 4, 1)
    t_tag = _utc(2026, 4, 15, 12, 0)
    t1 = _utc(2026, 5, 1)  # first_fix < t1, April fixes included
    with maker() as db:
        db.add(
            ProductionBug(
                id=1,
                jira_key="A-1",
                healthy=True,
                jira_created_at_valid=True,
                first_fix_release_date=t_tag,
                mttr_alpha_minutes=10,
            )
        )
        db.add(
            ProductionBug(
                id=2,
                jira_key="A-2",
                healthy=True,
                jira_created_at_valid=True,
                first_fix_release_date=t_tag,
                first_fix_release_tag="rel-a",
                mttr_alpha_minutes=20,
            )
        )
        db.add(
            ProductionBug(
                id=3,
                jira_key="A-3",
                healthy=True,
                jira_created_at_valid=True,
                first_fix_release_date=t_tag,
                mttr_alpha_minutes=30,
            )
        )
        db.add(
            ProductionBug(
                id=4,
                jira_key="A-4",
                healthy=True,
                jira_created_at_valid=True,
                first_fix_release_date=t_tag,
                first_fix_release_tag="rel-b",
                mttr_alpha_minutes=100,
            )
        )
        db.add(
            ProductionBug(
                id=5,
                jira_key="A-5",
                healthy=True,
                jira_created_at_valid=True,
                first_fix_release_date=t_tag,
                first_fix_release_tag="rel-b",
                mttr_alpha_minutes=200,
            )
        )
        db.commit()
        assert rds.median_mttr_alpha_minutes_in_window(db, period_start=t0, period_end=t0) is None
        med = rds.median_mttr_alpha_minutes_in_window(db, period_start=t0, period_end=t1)
        assert med == 30
        assert sorted(
            rds.list_mttr_alpha_minutes_in_window(db, period_start=t0, period_end=t1)
        ) == [10, 20, 30, 100, 200]
        paths = rds.list_mttr_alpha_resolution_path_counts(db, period_start=t0, period_end=t1)
        assert any(p.resolution_path == "unknown" for p in paths)
        page = rds.list_mttr_alpha_incidents_page(
            db, period_start=t0, period_end=t1, page=0, size=1, first_fix_release_tag="rel-b"
        )
        assert len(page) == 1
        assert page[0].jira_key == "A-5"
        assert rds.count_mttr_alpha_incidents_for_release_tag(
            db, period_start=t0, period_end=t1, first_fix_release_tag="rel-b"
        ) == 2
        rels = rds.list_mttr_alpha_releases_page(
            db, period_start=t0, period_end=t1, page=0, size=10
        )
        by_tag = {r.first_fix_release_tag: r for r in rels}
        assert by_tag["rel-b"].median_minutes == 150
        assert by_tag["rel-a"].median_minutes == 20
