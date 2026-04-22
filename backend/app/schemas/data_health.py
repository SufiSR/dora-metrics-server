from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.releases import OffsetPagination


class DataHealthSummary(BaseModel):
    total_bugs: int = Field(ge=0)
    healthy_bugs: int = Field(ge=0)
    healthy_bugs_pct: float = Field(ge=0.0, le=100.0)
    unmatched_mr_count: int = Field(ge=0)
    version_mismatch_count: int = Field(ge=0)


class JiraHealthBreakdownRow(BaseModel):
    healthy: bool
    healthmemo: str | None
    count: int = Field(ge=0)
    share_pct: float = Field(ge=0.0, le=100.0)


class UnmatchedMergeRequestRow(BaseModel):
    repository_id: int
    repository_path: str
    gitlab_mr_id: int
    title: str | None
    merged_at: datetime
    jira_key: str | None
    reason: str
    gitlab_merge_request_url: str | None = None
    jira_browse_url: str | None = None


class VersionMismatchRow(BaseModel):
    jira_key: str
    summary: str | None
    last_updated_at: datetime | None
    healthmemo: str | None
    affects_versions: list[str]
    fix_versions: list[str]
    unmatched_versions: list[str]
    reason: str
    jira_browse_url: str | None = None


class DataHealthResponse(BaseModel):
    generated_at: datetime
    summary: DataHealthSummary
    jira_health_breakdown: list[JiraHealthBreakdownRow]
    unmatched_merge_requests: list[UnmatchedMergeRequestRow]
    unmatched_merge_requests_pagination: OffsetPagination
    version_mismatches: list[VersionMismatchRow]
    version_mismatches_pagination: OffsetPagination
