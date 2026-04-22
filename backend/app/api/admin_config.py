from __future__ import annotations

import logging
import threading
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from app.api.deps import SessionDep, require_admin_session
from app.schemas.admin_config import (
    AdminConfigPatch,
    AdminConfigResponse,
    WebhookTestRequest,
    WebhookTestResponse,
)
from app.services.config_service import load_runtime_config
from app.services.admin_config_service import build_admin_config_response, patch_admin_configuration
from app.services.sync_pipeline import run_nightly_sync
from app.services.webhook_service import build_test_webhook_payload, send_webhook_notification

logger = logging.getLogger(__name__)

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


@router.post("/config/webhook/test", response_model=WebhookTestResponse)
def test_webhook(
    body: WebhookTestRequest,
    _auth: AdminSessionDep,
    db: SessionDep,
) -> WebhookTestResponse:
    runtime = load_runtime_config(db=db)
    draft_url = str(body.webhook_url).strip() if body.webhook_url is not None else ""
    effective_url = draft_url or (runtime.settings.notifications.webhook_url or "").strip()
    if not effective_url:
        raise HTTPException(status_code=400, detail="Webhook URL is not configured")
    payload = build_test_webhook_payload(trigger="manual")
    delivered = send_webhook_notification(effective_url, payload)
    return WebhookTestResponse(
        delivered=delivered,
        effective_webhook_url=effective_url,
        payload=payload,
    )


def _run_manual_sync_in_thread() -> None:
    try:
        run_nightly_sync(trigger="manual")
    except Exception:
        logger.exception("manual sync background thread failed")


@router.post("/sync/trigger", status_code=202)
def trigger_manual_sync(_auth: AdminSessionDep) -> JSONResponse:
    """Fire off a manual sync in the background and return immediately."""
    logger.info("admin requested manual sync_pipeline (dispatching background thread)")
    thread = threading.Thread(target=_run_manual_sync_in_thread, name="manual-sync", daemon=True)
    thread.start()
    return JSONResponse(status_code=202, content={"detail": "Sync triggered"})
