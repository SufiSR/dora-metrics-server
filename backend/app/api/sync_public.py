from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import RuntimeSettingsDep, SessionDep
from app.schemas.sync_status import SyncStatusResponse
from app.services.sync_status_service import build_sync_status_response

router = APIRouter()


@router.get("/status", response_model=SyncStatusResponse)
def get_sync_status(db: SessionDep, settings: RuntimeSettingsDep) -> SyncStatusResponse:
    return build_sync_status_response(db, config=settings)
