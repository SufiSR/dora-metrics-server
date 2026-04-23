"""Unit tests for data_health_service module-level helpers."""

from __future__ import annotations

from app.services import data_health_service as dhs


class _MR:
    first_customer_tag: str | None
    jira_key: str | None
    lead_time_match_status: str | None


def test_normalize_version_key_with_v_prefix() -> None:
    assert dhs._normalize_version_key("v1.2.3") == {"v1.2.3", "1.2.3"}
    assert dhs._normalize_version_key("1.2.3") == {"1.2.3", "v1.2.3"}


def test_mr_unmatched_reason_variants() -> None:
    mr = _MR()
    mr.first_customer_tag = None
    mr.jira_key = None
    mr.lead_time_match_status = None
    assert dhs._mr_unmatched_reason(mr) == "no_customer_release_tag"  # type: ignore[arg-type]
    mr.first_customer_tag = "t"
    assert dhs._mr_unmatched_reason(mr) == "missing_jira_key"  # type: ignore[arg-type]
    mr.jira_key = "K-1"
    mr.lead_time_match_status = "pending"
    assert dhs._mr_unmatched_reason(mr) == "lead_time_pending"  # type: ignore[arg-type]
    mr.lead_time_match_status = "matched"
    assert dhs._mr_unmatched_reason(mr) is None  # type: ignore[arg-type]


def test_list_jira_breakdown_empty_total() -> None:
    class _D:
        def execute(self, _q):  # type: ignore[no-untyped-def]
            return self

        def all(self):  # type: ignore[no-untyped-def]
            return [(True, "ok", 1)]

    rows = dhs._list_jira_health_breakdown(_D(), total_bugs=0)  # type: ignore[arg-type]
    assert rows == []


def test_offset_pagination_no_results() -> None:
    p = dhs._offset_pagination(page=0, size=20, total=0)
    assert p.total_pages == 0
    assert p.has_next is False
