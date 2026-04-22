from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

import httpx

WebhookEvent = Literal[
    "SYNC_SUCCESS",
    "SYNC_PARTIAL_FAILURE",
    "SYNC_COMPLETE_FAILURE",
    "SYNC_TEST",
]
WebhookStatus = Literal["success", "partial_failure", "failed", "test"]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _collector_counts(details_json: dict[str, Any], collector: str) -> dict[str, int]:
    collectors = details_json.get("collectors")
    if not isinstance(collectors, dict):
        return {}
    collector_block = collectors.get(collector)
    if not isinstance(collector_block, dict):
        return {}
    records = collector_block.get("records_processed")
    if not isinstance(records, dict):
        return {}
    return {str(k): int(v) for k, v in records.items() if isinstance(v, int)}


def build_webhook_payload(
    *,
    event: WebhookEvent,
    status: WebhookStatus,
    trigger: str,
    records_processed: int,
    details_json: dict[str, Any] | None = None,
    errors: list[str] | None = None,
    metadata: dict[str, str | int | bool | None] | None = None,
) -> dict[str, Any]:
    details = details_json if isinstance(details_json, dict) else {}
    effective_errors = [str(item) for item in (errors or []) if str(item).strip()]
    payload: dict[str, Any] = {
        "event": event,
        "status": status,
        "trigger": trigger,
        "sent_at": _utc_now_iso(),
        "records_processed": records_processed,
        "duration_seconds": details.get("duration_seconds"),
        "started_at": details.get("started_at"),
        "finished_at": details.get("finished_at"),
        "snapshots_generated": details.get("snapshots_generated", 0),
        "collectors": {
            "gitlab": {
                "status": (
                    details.get("collectors", {}).get("gitlab", {}).get("status")
                    if isinstance(details.get("collectors"), dict)
                    else None
                ),
                "records_processed": _collector_counts(details, "gitlab"),
            },
            "jira": {
                "status": (
                    details.get("collectors", {}).get("jira", {}).get("status")
                    if isinstance(details.get("collectors"), dict)
                    else None
                ),
                "records_processed": _collector_counts(details, "jira"),
            },
        },
        "errors": effective_errors,
        "metadata": metadata or {},
    }
    return payload


def build_test_webhook_payload(*, trigger: str = "admin_test") -> dict[str, Any]:
    return build_webhook_payload(
        event="SYNC_TEST",
        status="test",
        trigger=trigger,
        records_processed=0,
        details_json={
            "duration_seconds": 0,
            "started_at": _utc_now_iso(),
            "finished_at": _utc_now_iso(),
            "snapshots_generated": 0,
            "collectors": {
                "gitlab": {"status": "SUCCESS", "records_processed": {"repositories": 0}},
                "jira": {"status": "SUCCESS", "records_processed": {"bugs": 0}},
            },
        },
        metadata={"source": "admin", "is_test": True},
    )


def send_webhook_notification(
    url: str | None,
    payload: dict[str, Any],
    *,
    raise_on_error: bool = False,
) -> bool:
    if not url:
        return False
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(url, json=payload)
        response.raise_for_status()
        return True
    except Exception:
        if raise_on_error:
            raise
        return False
