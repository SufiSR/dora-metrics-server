from __future__ import annotations

from app.services.gitlab_release_collector import (
    _deduplicate_merge_requests,
    _effective_commit_sha,
    _extract_jira_key,
    _is_customer_release,
    _markers_regex,
    parse_tag_version,
)


def test_parse_tag_version_semver_with_prerelease() -> None:
    parsed = parse_tag_version("v10.2.3-rc.1")
    assert parsed.major == 10
    assert parsed.minor == 2
    assert parsed.patch == 3
    assert parsed.pre_release == "rc.1"


def test_parse_tag_version_non_semver_returns_none_fields() -> None:
    parsed = parse_tag_version("release-2026-03")
    assert parsed.major is None
    assert parsed.minor is None
    assert parsed.patch is None
    assert parsed.pre_release is None


def test_customer_release_false_for_configured_markers() -> None:
    marker_re = _markers_regex(["rc", "beta"])
    assert _is_customer_release("v10.1.0-rc.1", marker_re) is False
    assert _is_customer_release("v10.1.0-beta", marker_re) is False


def test_customer_release_true_for_final_version() -> None:
    marker_re = _markers_regex(["rc", "beta"])
    assert _is_customer_release("v10.1.0", marker_re) is True


def test_extract_jira_key_prefers_title_over_branch_description() -> None:
    jira_key, jira_key_source = _extract_jira_key(
        title="DEVOPS-433 implement collector",
        source_branch="feature/DEVOPS-999-something",
        description="fallback DEVOPS-888",
    )
    assert jira_key == "DEVOPS-433"
    assert jira_key_source == "title"


def test_extract_jira_key_falls_back_to_branch_then_description() -> None:
    jira_key, jira_key_source = _extract_jira_key(
        title="no issue key here",
        source_branch="feature/DEVOPS-777-fast-path",
        description="also has DEVOPS-666",
    )
    assert jira_key == "DEVOPS-777"
    assert jira_key_source == "branch"

    jira_key, jira_key_source = _extract_jira_key(
        title="no key",
        source_branch="feature/no-key",
        description="References DEVOPS-555 in details.",
    )
    assert jira_key == "DEVOPS-555"
    assert jira_key_source == "description"


def test_effective_commit_sha_prefers_merge_then_squash() -> None:
    assert _effective_commit_sha("abc123", "def456") == "abc123"
    assert _effective_commit_sha(None, "def456") == "def456"
    assert _effective_commit_sha("", "def456") == "def456"
    assert _effective_commit_sha(None, None) is None


def test_deduplicate_merge_requests_by_gitlab_id() -> None:
    merge_requests = [
        {"gitlab_mr_id": 42, "merged_at": "2026-03-31T08:00:00+00:00", "target_branch": "master"},
        {"gitlab_mr_id": 17, "merged_at": "2026-03-31T09:00:00+00:00", "target_branch": "10.x"},
        {"gitlab_mr_id": 42, "merged_at": "2026-03-31T08:00:00+00:00", "target_branch": "11.x"},
    ]
    deduplicated = _deduplicate_merge_requests(merge_requests)

    assert len(deduplicated) == 2
    ids = [item["gitlab_mr_id"] for item in deduplicated]
    assert ids == [17, 42]
