"""Tests for events.py — EventLog bounding/ordering and diff_events'
change-detection (never emits on the first poll, never floods on routine
unchanged polls)."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parents[1] / ".automation" / "night-shift" / "dashboard" / "backend"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, _BACKEND_DIR / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


events_mod = _load("events")


class TestEventLog:
    def test_recent_returns_newest_first(self):
        log = events_mod.EventLog()
        log.add("info", "first", ts=100.0)
        log.add("info", "second", ts=200.0)
        log.add("info", "third", ts=300.0)
        recent = log.recent()
        assert [e["message"] for e in recent] == ["third", "second", "first"]

    def test_bounded_by_max_events(self):
        log = events_mod.EventLog(max_events=3)
        for i in range(10):
            log.add("info", f"event-{i}", ts=float(i))
        recent = log.recent(limit=100)
        assert len(recent) == 3
        assert recent[0]["message"] == "event-9"

    def test_pruned_by_age(self):
        log = events_mod.EventLog(max_age_seconds=100.0)
        log.add("info", "old", ts=0.0)
        log.add("info", "new", ts=1000.0)  # triggers prune, cutoff = 1000-100=900
        recent = log.recent()
        assert [e["message"] for e in recent] == ["new"]


class TestDiffEvents:
    def test_first_poll_emits_nothing(self):
        assert events_mod.diff_events(None, {"processed": 100}) == []

    def test_unchanged_snapshot_emits_nothing(self):
        snap = {"processed": 100, "total": 200, "errors": 0, "process_alive": True,
                "ollama_online": True, "n8n_online": True, "queue": {"Vol01": "RUNNING"},
                "queue_stopped": False, "active": "Vol01"}
        assert events_mod.diff_events(snap, dict(snap)) == []

    def test_checkpoint_change_emits_info(self):
        prev = {"processed": 100, "total": 5452, "percentage": 1.8, "active": "Vol01"}
        cur = {"processed": 200, "total": 5452, "percentage": 3.7, "active": "Vol01"}
        result = events_mod.diff_events(prev, cur)
        assert len(result) == 1
        assert result[0][0] == "info"
        assert "200/5452" in result[0][1]

    def test_error_increase_emits_warn(self):
        prev = {"errors": 0}
        cur = {"errors": 3}
        result = events_mod.diff_events(prev, cur)
        assert ("warn", "llm_errors increased: 0 -> 3") in result

    def test_process_death_emits_error(self):
        prev = {"process_alive": True}
        cur = {"process_alive": False}
        result = events_mod.diff_events(prev, cur)
        assert result == [("error", "TSU process stopped")]

    def test_process_recovery_emits_info(self):
        prev = {"process_alive": False}
        cur = {"process_alive": True}
        result = events_mod.diff_events(prev, cur)
        assert result == [("info", "TSU process resumed")]

    def test_ollama_offline_then_online(self):
        assert events_mod.diff_events({"ollama_online": True}, {"ollama_online": False}) == [
            ("error", "Ollama offline")
        ]
        assert events_mod.diff_events({"ollama_online": False}, {"ollama_online": True}) == [
            ("info", "Ollama back online")
        ]

    def test_queue_transition_to_failed_is_error_level(self):
        prev = {"queue": {"Vol02": "RUNNING"}}
        cur = {"queue": {"Vol02": "FAILED"}}
        result = events_mod.diff_events(prev, cur)
        assert result == [("error", "Vol02: RUNNING -> FAILED")]

    def test_queue_transition_to_complete_is_info_level(self):
        prev = {"queue": {"Vol01": "RUNNING"}}
        cur = {"queue": {"Vol01": "COMPLETE"}}
        result = events_mod.diff_events(prev, cur)
        assert result == [("info", "Vol01: RUNNING -> COMPLETE")]

    def test_queue_stopped_emits_error_with_reason(self):
        prev = {"queue_stopped": False}
        cur = {"queue_stopped": True, "queue_stop_reason": "Vol03 FAILED"}
        result = events_mod.diff_events(prev, cur)
        assert result == [("error", "queue stopped — Vol03 FAILED")]
