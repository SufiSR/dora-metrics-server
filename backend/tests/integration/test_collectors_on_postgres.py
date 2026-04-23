"""
Collectors end-to-end on PostgreSQL with real `GitLabTagsClient` / `JiraBugsClient` and
`respx` mocking the actual `httpx` transport (no in-process fakes on client classes).
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import quote

import httpx
import pytest
import respx
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.config_schema import ConfigurationSchema
from app.models.production_bug import ProductionBug
from app.models.release import Release
from app.models.sync_log import SyncLog
from app.services.gitlab_release_collector import collect_gitlab_tags_and_releases
from app.services.jira_bug_collector import collect_jira_production_bugs

pytestmark = pytest.mark.integration

_GITLAB_BASE = "https://gitlab.respx.test"
_JIRA_BASE = "https://jira.respx.test"
_PROJECT_PATH = "integration/http-sample"
# Must match respx GitLab "id" in project JSON; repository.id is set to this.
_GITLAB_PROJECT_ID = 99_220
# Unique per suite run vs older integration tests
_JIRA_KEY = "RSPX-9001"
_TAG = "v10.0.0"
_COMMIT = "a" * 40


def _gitlab_encoded_path() -> str:
    return quote(_PROJECT_PATH, safe="")


@respx.mock
def test_gitlab_collector_uses_httpx_and_persists_release(
    session_factory: sessionmaker[Session],
) -> None:
    enc = _gitlab_encoded_path()
    r_project = respx.get(
        re.compile(rf"^{re.escape(_GITLAB_BASE)}/api/v4/projects/{re.escape(enc)}$")
    ).mock(
        return_value=httpx.Response(
            200,
            json={
                "id": _GITLAB_PROJECT_ID,
                "name": "repo",
                "path_with_namespace": _PROJECT_PATH,
                "default_branch": "main",
            },
        )
    )
    r_tags = respx.get(
        re.compile(
            rf"^{re.escape(_GITLAB_BASE)}/api/v4/projects/{re.escape(enc)}/repository/tags\?"
        )
    ).mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "name": _TAG,
                    "commit": {
                        "id": _COMMIT,
                        "committed_date": "2026-04-10T12:00:00Z",
                    },
                }
            ],
        )
    )
    r_mrs = respx.get(
        re.compile(
            rf"^{re.escape(_GITLAB_BASE)}/api/v4/projects/{re.escape(enc)}/merge_requests\?"
        )
    ).mock(return_value=httpx.Response(200, json=[]))

    cfg = ConfigurationSchema.model_validate(
        {
            "gitlab": {
                "base_url": _GITLAB_BASE,
                "project_paths": [_PROJECT_PATH],
                "target_branches": ["main"],
            },
            "backend": {"lookback_days": 30},
        }
    )
    with session_factory() as db:
        processed = collect_gitlab_tags_and_releases(
            db,
            config=cfg,
            gitlab_token="glpat-respx-integration",
            mr_mapping_cooldown_seconds=0.0,
        )
        log = db.scalars(
            select(SyncLog).where(SyncLog.source == "gitlab").order_by(SyncLog.id.desc())
        ).first()
        tag_names = list(
            db.scalars(
                select(Release.tag_name).where(Release.repository_id == _GITLAB_PROJECT_ID)
            ).all()
        )

    assert r_project.called
    assert r_tags.called
    assert r_mrs.called
    assert processed >= 1
    assert log is not None
    assert log.status == "success"
    assert log.records_processed == processed
    assert _TAG in tag_names


@respx.mock
def test_jira_collector_uses_httpx_and_persists_bug(
    session_factory: sessionmaker[Session],
) -> None:
    enc_key = quote(_JIRA_KEY, safe="")
    issue: dict[str, Any] = {
        "key": _JIRA_KEY,
        "changelog": {
            "histories": [
                {
                    "created": "2026-04-01T09:00:00.000+0000",
                    "items": [{"field": "status", "toString": "Ready for QA"}],
                }
            ],
            "total": 1,
        },
        "fields": {
            "summary": "Respx transport bug",
            "issuetype": {"name": "Bug"},
            "status": {"name": "Closed"},
            "priority": {"name": "Critical"},
            "created": "2026-04-01T08:00:00.000+0000",
            "updated": "2026-04-02T08:00:00.000+0000",
            "resolutiondate": "2026-04-03T08:00:00.000+0000",
            "versions": [{"name": "10.0.0"}],
            "fixVersions": [{"name": "10.0.1"}],
            "components": [],
            "customfield_10114": "https://help.example/browse/CS-1",
            "customfield_10123": [{"name": "Acme Corp"}],
        },
    }
    r_search = respx.get(
        re.compile(rf"^{re.escape(_JIRA_BASE)}/rest/api/3/search/jql\?.*")
    ).mock(
        return_value=httpx.Response(200, json={"issues": [issue]}),
    )
    r_wl = respx.get(
        re.compile(
            rf"^{re.escape(_JIRA_BASE)}/rest/api/3/issue/{re.escape(enc_key)}/worklog\?"
        )
    ).mock(
        return_value=httpx.Response(
            200,
            json={"startAt": 0, "maxResults": 100, "total": 0, "worklogs": []},
        )
    )

    cfg = ConfigurationSchema.model_validate(
        {
            "jira": {
                "base_url": _JIRA_BASE,
                "ready_for_qa_status_names": ["Ready for QA"],
            },
            "backend": {"lookback_days": 14},
        }
    )
    with session_factory() as db:
        processed = collect_jira_production_bugs(
            db,
            config=cfg,
            jira_token="jira-respx-token",
            jira_user_email="jira.test@respx.example",
        )
        log = db.scalars(
            select(SyncLog).where(SyncLog.source == "jira").order_by(SyncLog.id.desc())
        ).first()
        bug = db.scalars(select(ProductionBug).where(ProductionBug.jira_key == _JIRA_KEY)).first()

    assert r_search.called
    assert r_wl.called
    assert processed == 1
    assert log is not None and log.status == "success"
    assert bug is not None
    assert bug.healthy is True
    assert bug.ready_for_qa_at is not None
