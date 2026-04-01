from __future__ import annotations

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.api.deps import SessionDep
from app.models.repository import Repository
from app.schemas.repositories import RepositoriesResponse, RepositoryItem

router = APIRouter()


@router.get("", response_model=RepositoriesResponse)
def list_repositories(
    db: SessionDep,
    active: bool = Query(default=True, description="When true, only active repositories"),
) -> RepositoriesResponse:
    q = select(Repository).order_by(Repository.path)
    q = q.where(Repository.active.is_(active))
    rows = list(db.scalars(q).all())
    items = [
        RepositoryItem(
            id=int(r.id),
            gitlab_id=int(r.gitlab_id),
            name=r.name,
            path=r.path,
            default_branch=r.default_branch,
            active=bool(r.active),
        )
        for r in rows
    ]
    return RepositoriesResponse(repositories=items, total=len(items))
