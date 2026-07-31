"""Tests for core/background_index_builder.py (DBMA-SEARCH-INFRA-001 HQ 제안 ⑧)."""

import time

import pytest

import core.background_index_builder as bib_module
from core.background_index_builder import BackgroundIndexBuilder


def _wait_until(predicate, timeout=2.0, interval=0.02):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return predicate()


class TestStartStop:
    def test_start_marks_alive(self, monkeypatch):
        monkeypatch.setattr(bib_module, "reconcile_pending", lambda output_dir: {"pending": 0, "reconciled": 0, "failed": [], "purged": 0})
        builder = BackgroundIndexBuilder(interval_seconds=0.05)
        builder.start()
        assert _wait_until(lambda: builder.status()["is_alive"])
        builder.stop()

    def test_start_is_idempotent(self, monkeypatch):
        monkeypatch.setattr(bib_module, "reconcile_pending", lambda output_dir: {"pending": 0, "reconciled": 0, "failed": [], "purged": 0})
        builder = BackgroundIndexBuilder(interval_seconds=0.05)
        builder.start()
        builder.start()  # should not raise or spawn a second thread
        assert builder.status()["is_alive"]
        builder.stop()

    def test_stop_marks_not_alive(self, monkeypatch):
        monkeypatch.setattr(bib_module, "reconcile_pending", lambda output_dir: {"pending": 0, "reconciled": 0, "failed": [], "purged": 0})
        builder = BackgroundIndexBuilder(interval_seconds=0.05)
        builder.start()
        _wait_until(lambda: builder.status()["is_alive"])
        builder.stop()
        assert not builder.status()["is_alive"]


class TestTriggerNow:
    def test_trigger_now_runs_promptly_without_waiting_for_interval(self, monkeypatch):
        call_count = {"n": 0}

        def fake_reconcile(output_dir):
            call_count["n"] += 1
            return {"pending": 0, "reconciled": 1, "failed": [], "purged": 0}

        monkeypatch.setattr(bib_module, "reconcile_pending", fake_reconcile)
        # Long interval — if trigger_now() didn't wake it immediately, the
        # test would have to wait out the whole interval to see a call.
        builder = BackgroundIndexBuilder(interval_seconds=30.0)
        builder.start()
        builder.trigger_now()
        assert _wait_until(lambda: call_count["n"] >= 1, timeout=2.0)
        builder.stop()

    def test_trigger_now_before_start_is_not_lost(self, monkeypatch):
        # trigger_now() sets an Event, which persists until start()'s loop
        # consumes it — the first loop iteration should fire immediately.
        call_count = {"n": 0}
        monkeypatch.setattr(
            bib_module, "reconcile_pending",
            lambda output_dir: (call_count.__setitem__("n", call_count["n"] + 1), {"pending": 0, "reconciled": 0, "failed": [], "purged": 0})[1],
        )
        builder = BackgroundIndexBuilder(interval_seconds=30.0)
        builder.trigger_now()
        builder.start()
        assert _wait_until(lambda: call_count["n"] >= 1, timeout=2.0)
        builder.stop()


class TestStatus:
    def test_last_result_reflects_reconcile_output(self, monkeypatch):
        monkeypatch.setattr(
            bib_module, "reconcile_pending",
            lambda output_dir: {"pending": 2, "reconciled": 2, "failed": [], "purged": 0},
        )
        builder = BackgroundIndexBuilder(interval_seconds=0.05)
        builder.start()
        builder.trigger_now()
        assert _wait_until(lambda: builder.status()["last_result"] is not None)
        assert builder.status()["last_result"]["reconciled"] == 2
        builder.stop()

    def test_exception_captured_not_raised_and_thread_survives(self, monkeypatch):
        calls = {"n": 0}

        def flaky_reconcile(output_dir):
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("boom")
            return {"pending": 0, "reconciled": 1, "failed": [], "purged": 0}

        monkeypatch.setattr(bib_module, "reconcile_pending", flaky_reconcile)
        builder = BackgroundIndexBuilder(interval_seconds=0.05)
        builder.start()
        builder.trigger_now()
        assert _wait_until(lambda: builder.status()["last_error"] == "boom")
        assert builder.status()["is_alive"]  # thread must still be running

        builder.trigger_now()
        assert _wait_until(lambda: builder.status()["last_result"] is not None)
        builder.stop()

    def test_is_running_job_true_while_reconcile_is_slow(self, monkeypatch):
        def slow_reconcile(output_dir):
            time.sleep(0.3)
            return {"pending": 0, "reconciled": 0, "failed": [], "purged": 0}

        monkeypatch.setattr(bib_module, "reconcile_pending", slow_reconcile)
        builder = BackgroundIndexBuilder(interval_seconds=30.0)
        builder.start()
        builder.trigger_now()
        assert _wait_until(lambda: builder.status()["is_running_job"], timeout=1.0)
        assert _wait_until(lambda: not builder.status()["is_running_job"], timeout=1.0)
        builder.stop()
