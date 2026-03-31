from __future__ import annotations

from datetime import datetime, timezone

from app.services.jira_bug_collector import (
    evaluate_issue_health,
    first_ready_for_qa_at,
    parse_worklog_entry,
)


def test_health_healthy_post_production() -> None:
    result = evaluate_issue_health(
        issue_type="Bug",
        parent_type=None,
        parent_summary=None,
        affects_versions=["10.1.0"],
        fix_versions=["10.1.1"],
        indicator_cf10114="https://plunethelp.atlassian.net/browse/CS-123",
        customer_names=[],
        parent_affects_versions=[],
        parent_fix_versions=[],
        parent_indicator_cf10114=None,
        parent_customer_names=[],
    )
    assert result.healthy is True
    assert result.healthmemo == "post-production"


def test_health_pre_production_parent_override() -> None:
    result = evaluate_issue_health(
        issue_type="Bug Subtask",
        parent_type="Improvement",
        parent_summary="Work package",
        affects_versions=[],
        fix_versions=[],
        indicator_cf10114=None,
        customer_names=[],
        parent_affects_versions=[],
        parent_fix_versions=[],
        parent_indicator_cf10114=None,
        parent_customer_names=[],
    )
    assert result.healthy is True
    assert "pre-production - parent is Improvement" == result.healthmemo


def test_health_parent_second_pass_rescue() -> None:
    result = evaluate_issue_health(
        issue_type="Bug Subtask",
        parent_type="Bug",
        parent_summary="Incident parent",
        affects_versions=[],
        fix_versions=[],
        indicator_cf10114=None,
        customer_names=[],
        parent_affects_versions=["10.2.0"],
        parent_fix_versions=[],
        parent_indicator_cf10114="https://plunethelp.atlassian.net/browse/CS-999",
        parent_customer_names=[],
    )
    assert result.healthy is True
    assert result.healthmemo == "post-production due to parent"


def test_health_next_minor_global_override() -> None:
    result = evaluate_issue_health(
        issue_type="Bug",
        parent_type=None,
        parent_summary=None,
        affects_versions=["next minor - please branch from master"],
        fix_versions=[],
        indicator_cf10114=None,
        customer_names=[],
        parent_affects_versions=[],
        parent_fix_versions=[],
        parent_indicator_cf10114=None,
        parent_customer_names=[],
    )
    assert result.healthy is True
    assert result.healthmemo == "post-production - next minor stated"


def test_parse_worklog_entry() -> None:
    parsed = parse_worklog_entry(
        {
            "id": "1234",
            "timeSpentSeconds": 7200,
            "started": "2026-03-31T09:00:00.000+0000",
            "author": {"displayName": "A User"},
        }
    )
    assert parsed is not None
    assert parsed["jira_worklog_id"] == "1234"
    assert parsed["time_spent_seconds"] == 7200
    assert parsed["author"] == "A User"


def test_first_ready_for_qa_at_uses_earliest_transition() -> None:
    ready_for_qa = first_ready_for_qa_at(
        [
            {
                "created": "2026-03-31T10:00:00.000+0000",
                "items": [{"field": "status", "toString": "Ready for test"}],
            },
            {
                "created": "2026-03-31T09:00:00.000+0000",
                "items": [{"field": "status", "toString": "Ready for QA"}],
            },
        ],
        ["Ready for QA", "Ready for test"],
    )
    assert ready_for_qa == datetime(2026, 3, 31, 9, 0, tzinfo=timezone.utc)
