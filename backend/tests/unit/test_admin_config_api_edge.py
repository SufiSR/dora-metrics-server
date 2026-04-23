"""Edge-case coverage for admin_config API module helpers."""

from __future__ import annotations

import logging

import pytest

import app.api.admin_config as ac


def test_run_manual_sync_in_thread_logs_exception(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _boom(**_kwargs: object) -> None:
        raise RuntimeError("unit test background sync failure")

    monkeypatch.setattr(ac, "run_nightly_sync", _boom)
    caplog.set_level(logging.ERROR)
    ac._run_manual_sync_in_thread()
    assert "manual sync background" in caplog.text
