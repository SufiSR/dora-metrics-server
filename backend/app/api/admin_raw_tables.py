from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import SessionDep, require_admin_session
from app.schemas.admin_raw_table import RawTableResponse
from app.services.admin_raw_table_service import SortDirection, list_admin_raw_table_rows

router = APIRouter()
AdminSessionDep = Annotated[None, Depends(require_admin_session)]


@router.get("/raw-tables/{table_name}", response_model=RawTableResponse)
def get_admin_raw_table_rows(
    _auth: AdminSessionDep,
    db: SessionDep,
    table_name: str,
    page: Annotated[int, Query(ge=0)] = 0,
    size: Annotated[int, Query(ge=1, le=200)] = 20,
    search: str | None = None,
    sort_by: str | None = None,
    sort_dir: SortDirection = SortDirection.DESC,
) -> RawTableResponse:
    try:
        return list_admin_raw_table_rows(
            db,
            table_name=table_name,
            page=page,
            size=size,
            search=search,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
