"""Unit tests for webhook payload construction and delivery."""

from __future__ import annotations

from unittest.mock import MagicMock

import httpx
import pytest

from app.services import webhook_service as ws


def test_build_webhook_payload_coerces_non_dict_details() -> None:
    payload = ws.build_webhook_payload(
        event="SYNC_SUCCESS",
        status="success",
        trigger="nightly",
        records_processed=5,
        details_json=None,  # type: ignore[arg-type]
    )
    assert payload["event"] == "SYNC_SUCCESS"
    assert payload["collectors"]["gitlab"]["records_processed"] == {}
    assert payload["metadata"] == {}


def test_build_webhook_payload_collectors_and_metadata() -> None:
    details = {
        "duration_seconds": 12,
        "started_at": "t0",
        "finished_at": "t1",
        "snapshots_generated": 2,
        "collectors": {
            "gitlab": {
                "status": "OK",
                "records_processed": {"repositories": 3, "bad": "skip", 9: 1},
            },
            "jira": {"status": "SKIP", "records_processed": {"bugs": 2}},
        },
    }
    payload = ws.build_webhook_payload(
        event="SYNC_PARTIAL_FAILURE",
        status="partial_failure",
        trigger="manual",
        records_processed=9,
        details_json=details,
        errors=["  ", "timeout"],
        metadata={"k": 1, "b": True},
    )
    assert payload["duration_seconds"] == 12
    assert payload["snapshots_generated"] == 2
    assert payload["collectors"]["gitlab"]["status"] == "OK"
    assert payload["collectors"]["gitlab"]["records_processed"] == {"9": 1, "repositories": 3}
    assert payload["collectors"]["jira"]["status"] == "SKIP"
    assert payload["collectors"]["jira"]["records_processed"] == {"bugs": 2}
    assert payload["errors"] == ["timeout"]


def test_collector_counts_non_dict_block() -> None:
    d = {"collectors": {"gitlab": "not-a-dict"}}
    assert ws._collector_counts(d, "gitlab") == {}


def test_collector_counts_skips_malformed_blocks() -> None:
    p = ws.build_webhook_payload(
        event="SYNC_SUCCESS",
        status="success",
        trigger="n",
        records_processed=0,
        details_json={
            "collectors": {
                "gitlab": {"status": "OK", "records_processed": "not-a-dict"},
                "jira": {"status": None, "records_processed": None},
            }
        },
    )
    assert p["collectors"]["gitlab"]["records_processed"] == {}
    assert p["collectors"]["jira"]["records_processed"] == {}


def test_build_test_webhook_payload_shape() -> None:
    p = ws.build_test_webhook_payload(trigger="x")
    assert p["event"] == "SYNC_TEST"
    assert p["status"] == "test"
    assert p["metadata"]["is_test"] is True
    assert p["collectors"]["gitlab"]["status"] == "SUCCESS"


def test_send_webhook_no_url() -> None:
    assert ws.send_webhook_notification(None, {"a": 1}) is False


def test_send_webhook_post_success(monkeypatch: pytest.MonkeyPatch) -> None:
    posted: list[tuple[str, object]] = []

    class _Resp:
        def raise_for_status(self) -> None:
            return None

    class _Client:
        def __enter__(self) -> _Client:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def post(self, url: str, json: object | None = None) -> _Resp:  # noqa: ANN201
            posted.append((url, json))
            return _Resp()

    monkeypatch.setattr(httpx, "Client", lambda timeout=10.0: _Client())
    ok = ws.send_webhook_notification("https://hook.example/h", {"status": "ok"})
    assert ok is True
    assert posted[0][0] == "https://hook.example/h"


def test_send_webhook_silent_on_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    class _BadResp:
        def raise_for_status(self) -> None:
            raise httpx.HTTPStatusError("bad", request=MagicMock(), response=MagicMock())

    class _Client:
        def __enter__(self) -> _Client:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def post(self, url: str, json: object | None = None) -> _BadResp:  # noqa: ANN201
            return _BadResp()

    monkeypatch.setattr(httpx, "Client", lambda timeout=10.0: _Client())
    assert ws.send_webhook_notification("https://hook.example/bad", {"x": 1}) is False


def test_send_webhook_raise_on_error_propagates(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Client:
        def __enter__(self) -> _Client:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def post(self, url: str, json: object | None = None) -> object:  # noqa: ANN201
            raise OSError("network down")

    monkeypatch.setattr(httpx, "Client", lambda timeout=10.0: _Client())
    with pytest.raises(OSError, match="network down"):
        ws.send_webhook_notification("https://hook.example/x", {}, raise_on_error=True)
