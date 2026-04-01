from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import SessionDep, require_admin_session
from app.schemas.admin_config import AdminConfigPatch, AdminConfigResponse
from app.services.admin_config_service import build_admin_config_response, patch_admin_configuration

router = APIRouter()

AdminSessionDep = Annotated[None, Depends(require_admin_session)]


@router.get("/config", response_model=AdminConfigResponse)
def get_admin_config(
    _auth: AdminSessionDep,
    db: SessionDep,
) -> AdminConfigResponse:
    return build_admin_config_response(db)


@router.patch("/config", response_model=AdminConfigResponse)
def patch_admin_config(
    body: AdminConfigPatch,
    _auth: AdminSessionDep,
    db: SessionDep,
) -> AdminConfigResponse:
    return patch_admin_configuration(db, body)
