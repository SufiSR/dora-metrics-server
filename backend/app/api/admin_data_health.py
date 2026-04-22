from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import RuntimeSettingsDep, SessionDep, require_admin_session
from app.schemas.data_health import DataHealthResponse
from app.services.data_health_service import build_data_health_response

router = APIRouter()
AdminSessionDep = Annotated[None, Depends(require_admin_session)]


@router.get("/data-health", response_model=DataHealthResponse)
def get_data_health(
    _auth: AdminSessionDep,
    db: SessionDep,
    settings: RuntimeSettingsDep,
    unmatched_page: Annotated[int, Query(ge=0)] = 0,
    unmatched_size: Annotated[int, Query(ge=1, le=200)] = 20,
    mismatch_page: Annotated[int, Query(ge=0)] = 0,
    mismatch_size: Annotated[int, Query(ge=1, le=200)] = 20,
) -> DataHealthResponse:
    return build_data_health_response(
        db,
        unmatched_page=unmatched_page,
        unmatched_size=unmatched_size,
        mismatch_page=mismatch_page,
        mismatch_size=mismatch_size,
        jira_base_url=settings.jira.base_url,
        gitlab_base_url=settings.gitlab.base_url,
    )
