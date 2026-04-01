from __future__ import annotations

from pydantic import BaseModel


class RepositoryItem(BaseModel):
    id: int
    gitlab_id: int
    name: str
    path: str
    default_branch: str
    active: bool


class RepositoriesResponse(BaseModel):
    repositories: list[RepositoryItem]
    total: int
