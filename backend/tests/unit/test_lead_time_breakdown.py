"""Unit tests for lead time branch/stream breakdown (DEVOPS-510)."""

from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.config_schema import ConfigurationSchema, GitLabConfig
from app.models import Base
from app.models.merge_request import MergeRequest
from app.models.repository import Repository
from app.services.lead_time_breakdown import (
    _MrLeadRow,
    active_repository_ids,
    change_stream_for_target_branch,
    fetch_lead_cohort_rows,
    fetch_lead_cohort_rows_range,
    group_rows_by_period,
    lead_time_bucket_dict,
    primary_feature_branch,
)


def _session_maker() -> sessionmaker[Session]:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)

    @event.listens_for(engine, "connect")
    def _fk(dbapi_conn, _rec):  # type: ignore[no-untyped-def]
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, class_=Session, autoflush=False, autocommit=False)


def test_primary_and_stream_mapping() -> None:
    cfg = ConfigurationSchema()
    assert primary_feature_branch(cfg) == "master"
    assert change_stream_for_target_branch("master", cfg) == "feature"
    assert change_stream_for_target_branch("10.x", cfg) == "patch"
    assert change_stream_for_target_branch("unknown-feature", cfg) == "other"


def test_primary_feature_branch_falls_back_when_no_branches() -> None:
    cfg = ConfigurationSchema(
        gitlab=GitLabConfig(
            project_paths=["x"],
            target_branches=[],
        )
    )
    assert primary_feature_branch(cfg) == "master"


def test_primary_feature_branch_custom_order() -> None:
    cfg = ConfigurationSchema(
        gitlab=GitLabConfig(
            project_paths=["x/y"],
            target_branches=["  develop  ", "10.x"],
        )
    )
    assert primary_feature_branch(cfg) == "develop"
    assert change_stream_for_target_branch("develop", cfg) == "feature"
    assert change_stream_for_target_branch("10.x", cfg) == "patch"


def test_change_stream_uses_additional_merge_branches() -> None:
    cfg = ConfigurationSchema(
        gitlab=GitLabConfig(
            target_branches=["main"],
            additional_merge_target_branches=["hotfix/line"],
        )
    )
    assert change_stream_for_target_branch("hotfix/line", cfg) == "patch"
    assert change_stream_for_target_branch("unlisted", cfg) == "other"


def test_lead_time_bucket_dict_stream() -> None:
    cfg = ConfigurationSchema()
    rows = [
        _MrLeadRow(
            target_branch="master",
            lead_time_hours=Decimal("10"),
            release_wait_time_hours=Decimal("4"),
            first_customer_tag_date=datetime(2026, 1, 15, tzinfo=timezone.utc),
        ),
        _MrLeadRow(
            target_branch="10.x",
            lead_time_hours=Decimal("20"),
            release_wait_time_hours=Decimal("5"),
            first_customer_tag_date=datetime(2026, 1, 16, tzinfo=timezone.utc),
        ),
    ]
    out = lead_time_bucket_dict(rows, mode="stream", config=cfg)
    assert "feature" in out and "patch" in out
    assert out["feature"]["sample_count"] == 1
    assert out["patch"]["sample_count"] == 1
    assert out["feature"]["median_lead_time_minutes"] == 600


def test_lead_time_bucket_dict_branch() -> None:
    cfg = ConfigurationSchema()
    rows = [
        _MrLeadRow(
            target_branch="master",
            lead_time_hours=Decimal("8"),
            release_wait_time_hours=Decimal("2"),
            first_customer_tag_date=datetime(2026, 2, 1, tzinfo=timezone.utc),
        ),
    ]
    out = lead_time_bucket_dict(rows, mode="branch", config=cfg)
    assert "master" in out
    assert out["master"]["sample_count"] == 1


def test_lead_time_bucket_dict_all_null_lead_times() -> None:
    cfg = ConfigurationSchema()
    rows = [
        _MrLeadRow(
            target_branch="master",
            lead_time_hours=None,
            release_wait_time_hours=Decimal("1"),
            first_customer_tag_date=datetime(2026, 1, 10, tzinfo=timezone.utc),
        ),
    ]
    out = lead_time_bucket_dict(rows, mode="stream", config=cfg)
    assert out["feature"]["median_lead_time_minutes"] is None


def test_lead_time_bucket_dict_stream_includes_other_key() -> None:
    """When any MR targets a branch outside feature/patch, an 'other' bucket appears."""
    cfg = ConfigurationSchema(
        gitlab=GitLabConfig(
            project_paths=["x"],
            target_branches=["master", "9.x", "10.x", "11.x"],
            additional_merge_target_branches=[],
        )
    )
    rows = [
        _MrLeadRow(
            target_branch="weird/line",
            lead_time_hours=Decimal("1"),
            release_wait_time_hours=Decimal("0.5"),
            first_customer_tag_date=datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc),
        ),
    ]
    out = lead_time_bucket_dict(rows, mode="stream", config=cfg)
    assert "other" in out
    assert out["other"]["sample_count"] == 1
    assert out["other"]["median_lead_time_minutes"] == 60
    # Negative dev-review delta is excluded from the median
    neg = [
        _MrLeadRow(
            target_branch="master",
            lead_time_hours=Decimal("1"),
            release_wait_time_hours=Decimal("5"),
            first_customer_tag_date=datetime(2026, 1, 2, tzinfo=timezone.utc),
        ),
    ]
    out2 = lead_time_bucket_dict(neg, mode="stream", config=cfg)
    assert out2["feature"]["dev_review_median_minutes"] is None


def test_group_rows_by_period_and_naive_tag() -> None:
    p0 = date(2026, 1, 1)
    p1 = date(2026, 1, 31)
    in_window = _MrLeadRow(
        target_branch="m",
        lead_time_hours=Decimal("1"),
        release_wait_time_hours=Decimal("1"),
        first_customer_tag_date=datetime(2026, 1, 15, 10, 0),  # naive, treated as UTC
    )
    out_window = _MrLeadRow(
        target_branch="m",
        lead_time_hours=Decimal("1"),
        release_wait_time_hours=Decimal("1"),
        first_customer_tag_date=datetime(2025, 12, 1, tzinfo=timezone.utc),
    )
    g = group_rows_by_period([in_window, out_window], p0, p1)
    assert len(g) == 1
    assert g[0] is in_window


def test_active_repository_ids_and_cohort_fetch() -> None:
    maker = _session_maker()
    t0 = datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc)
    cfg = ConfigurationSchema(
        gitlab=GitLabConfig(
            project_paths=["a"],
            target_branches=["master"],
        )
    )
    with maker() as db:
        assert active_repository_ids(db, repository_id=None) == []
        db.add(
            Repository(
                id=1,
                gitlab_id=1,
                name="a",
                path="g/a",
                default_branch="main",
                active=True,
            )
        )
        db.add(
            Repository(
                id=2,
                gitlab_id=2,
                name="b",
                path="g/b",
                default_branch="main",
                active=True,
            )
        )
        db.flush()
        for mid, rid, gid in ((1, 1, 110), (2, 2, 111)):
            db.add(
                MergeRequest(
                    id=mid,
                    repository_id=rid,
                    gitlab_mr_id=gid,
                    target_branch="master",
                    created_at=t0,
                    merged_at=t0,
                    first_customer_tag_date=t0,
                    lead_time_hours=Decimal("4"),
                    release_wait_time_hours=Decimal("1"),
                )
            )
        db.commit()
        assert sorted(active_repository_ids(db, repository_id=None)) == [1, 2]
        assert active_repository_ids(db, repository_id=2) == [2]
        r1 = fetch_lead_cohort_rows(
            db,
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
            repository_ids=[1, 2],
            config=cfg,
        )
        assert len(r1) == 2
        r2 = fetch_lead_cohort_rows_range(
            db,
            min_period_start=date(2026, 1, 1),
            max_period_end=date(2026, 1, 31),
            repository_ids=[1, 2],
            config=cfg,
        )
        assert len(r2) == 2
        assert fetch_lead_cohort_rows(
            db,
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
            repository_ids=[],
            config=cfg,
        ) == []
        assert (
            fetch_lead_cohort_rows_range(
                db,
                min_period_start=date(2026, 1, 1),
                max_period_end=date(2026, 1, 31),
                repository_ids=[],
                config=cfg,
            )
            == []
        )
