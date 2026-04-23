"""Tests for lead-time MR filter helpers in metric_service."""

from __future__ import annotations

from datetime import datetime, timezone

from app.config_schema import ConfigurationSchema, GitLabConfig
from app.services import metric_service as ms


def test_lead_time_filters_for_repos_empty_uses_sentinel() -> None:
    cfg = ConfigurationSchema()
    f = ms._lead_time_mr_filters_for_repos(
        start_dt=datetime(2026, 1, 1, tzinfo=timezone.utc),
        end_dt=datetime(2026, 2, 1, tzinfo=timezone.utc),
        repository_ids=[],
        config=cfg,
    )
    assert len(f) >= 4


def test_lead_time_filters_for_repos_single_id() -> None:
    cfg = ConfigurationSchema()
    f = ms._lead_time_mr_filters_for_repos(
        start_dt=datetime(2026, 1, 1, tzinfo=timezone.utc),
        end_dt=datetime(2026, 2, 1, tzinfo=timezone.utc),
        repository_ids=[5],
        config=cfg,
    )
    assert f


def test_merge_request_cohort_included_when_exclusion_off() -> None:
    cfg = ConfigurationSchema(
        gitlab=GitLabConfig(
            project_paths=["x"],
            exclude_release_only_mrs_from_lead_time=False,
        )
    )
    assert ms.merge_request_included_in_lead_time_cohort(
        title="weird release",
        source_branch="release",
        first_customer_tag_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
        config=cfg,
    )


def test_lead_time_exclusion_clauses_none_when_markers_blank() -> None:
    cfg = ConfigurationSchema()
    cfg.gitlab.exclude_release_only_mrs_from_lead_time = True
    cfg.gitlab.release_mr_title_markers = ["  ", ""]
    cfg.gitlab.release_mr_source_branch_markers = ["  "]
    assert ms._lead_time_mr_exclusion_clauses(cfg) is None


def test_merge_request_cohort_excluded_no_tag_date() -> None:
    cfg = ConfigurationSchema()
    assert not ms.merge_request_included_in_lead_time_cohort(
        title="x",
        source_branch="y",
        first_customer_tag_date=None,
        config=cfg,
    )
