from __future__ import annotations

from datetime import datetime, timezone

from app.services.gitlab_release_collector import (
    _deduplicate_merge_requests,
    _effective_commit_sha,
    _extract_jira_key,
    _hours_between,
    _is_customer_release,
    _markers_regex,
    _parse_merge_request,
    GitLabTagsClient,
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


def test_parse_merge_request_prefers_iid_for_gitlab_mr_id() -> None:
    parsed = _parse_merge_request(
        {
            "id": 9001,
            "iid": 42,
            "target_branch": "master",
            "created_at": "2026-03-31T08:00:00Z",
            "merged_at": "2026-03-31T09:00:00Z",
        }
    )
    assert parsed is not None
    assert parsed["gitlab_mr_id"] == 42


def test_hours_between_rounds_to_two_decimals() -> None:
    start = datetime(2026, 3, 31, 8, 0, tzinfo=timezone.utc)
    end = datetime(2026, 3, 31, 9, 20, 6, tzinfo=timezone.utc)
    assert str(_hours_between(start, end)) == "1.34"


def test_list_merge_request_commits_paginates() -> None:
    client = GitLabTagsClient(base_url="https://gitlab.example.com", token="dummy")
    responses = [
        [{"id": "c1"}, {"id": "c2"}],
        [{"id": "c3"}],
    ]

    def fake_get_json(url: str, *, params: dict[str, int] | None = None) -> object:
        assert "merge_requests/42/commits" in url
        assert params is not None
        return responses[params["page"] - 1]

    try:
        client._get_json = fake_get_json  # type: ignore[method-assign]
        commits = client.list_merge_request_commits("group/project", merge_request_iid=42, per_page=2)
        assert [item["id"] for item in commits] == ["c1", "c2", "c3"]
    finally:
        client.close()


def test_list_commit_tag_refs_paginates() -> None:
    client = GitLabTagsClient(base_url="https://gitlab.example.com", token="dummy")
    responses = [
        [{"name": "v1.0.0", "type": "tag"}, {"name": "v1.0.1", "type": "tag"}],
        [{"name": "v1.0.2", "type": "tag"}],
    ]

    def fake_get_json(url: str, *, params: dict[str, object] | None = None) -> object:
        assert "repository/commits/abc123/refs" in url
        assert params is not None
        assert params["type"] == "tag"
        return responses[int(params["page"]) - 1]

    try:
        client._get_json = fake_get_json  # type: ignore[method-assign]
        refs = client.list_commit_tag_refs("group/project", commit_sha="abc123", per_page=2)
        assert [item["name"] for item in refs] == ["v1.0.0", "v1.0.1", "v1.0.2"]
    finally:
        client.close()
