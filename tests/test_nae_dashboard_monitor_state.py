"""Tests for the polling orchestrator
(.automation/night-shift/dashboard/backend/monitor_state.py) — MonitorState
and PollLoop. Everything is driven through tmp_path fixtures and injected
reader callables (ps/ollama/n8n/memory/cpu/gpu/disk/network/thermal/
registration state), so nothing here touches the real filesystem outside
tmp_path or calls a real subprocess/network (same discipline as
test_nae_dashboard_collector.py — see memory: always override every
DEFAULT_*_PATH-style parameter in tests)."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_BACKEND_DIR = Path(__file__).resolve().parents[1] / ".automation" / "night-shift" / "dashboard" / "backend"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, _BACKEND_DIR / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


# Load in dependency order so `import collector` / `import events` etc.
# inside monitor_state.py resolve to these already-registered modules.
_load("collector")
_load("pipeline_stages")
_load("bottleneck")
_load("events")
_load("gpu_health")
monitor_state = _load("monitor_state")


PS_ACTIVE_VOL01 = (
    "David  88689  0.0  0.0 ...  ??  S  2:29PM  0:03.98 "
    "/opt/homebrew/.../Python -m NAE.pipeline.tsu.runner --identifier Fuller_Complete_Works_Vol01\n"
)
PS_IDLE = "David  123  0.0  0.0 ... some other process\n"

SAMPLE_IOREG_TEXT = (
    '+-o AGXAcceleratorG17X  <class AGXAcceleratorG17X, id 0x1000006f7, registered>\n'
    '    {\n'
    '      "PerformanceStatistics" = {"Device Utilization %"=87,"In use system memory"=54969483264}\n'
    '      "model" = "Apple M5 Max"\n'
    '      "gpu-core-count" = 40\n'
    '    }\n'
)


def _write_report(root: Path, identifier: str, **fields) -> None:
    out_dir = root / identifier
    out_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "identifier": identifier,
        "candidates_evaluated": 0,
        "candidates_total": 0,
        "llm_errors": 0,
        "elapsed_seconds": 0.0,
        "partial": True,
        **fields,
    }
    (out_dir / "tsu_report.json").write_text(json.dumps(report), encoding="utf-8")


def _write_tsu_records(root: Path, identifier: str, *statuses: str) -> None:
    out_dir = root / identifier
    out_dir.mkdir(parents=True, exist_ok=True)
    records = [{"id": f"TSU-{i:07d}", "review_status": s} for i, s in enumerate(statuses)]
    (out_dir / "tsu.json").write_text(json.dumps(records), encoding="utf-8")


def make_state(tmp_path, **overrides):
    defaults = dict(
        tsu_root=tmp_path / "tsu",
        queue_log_path=tmp_path / "queue.log",
        stop_marker_path=tmp_path / "STOP.md",
        ps_reader=lambda: PS_ACTIVE_VOL01,
        ollama_checker=lambda: True,
        n8n_checker=lambda: True,
        memory_reader=lambda: {"total_bytes": 137438953472, "used_bytes": 82696290304,
                                "available_bytes": 23069376512, "percent": 60.1},
        cpu_reader=lambda: {"percent": 18.9, "core_count": 18, "load_avg_1m": 8.5},
        gpu_reader=lambda: SAMPLE_IOREG_TEXT,
        disk_reader=lambda: {"total_bytes": 4000000000000, "used_bytes": 2000000000000, "percent": 50.0},
        disk_io_reader=lambda: {"read_bytes": 1000, "write_bytes": 2000},
        net_io_reader=lambda: {"bytes_sent": 500, "bytes_recv": 700},
        thermal_reader=lambda: "Note: No thermal warning level has been recorded\n",
        ollama_models_reader=lambda: [{"name": "my-theology-bot-v2:latest"}],
        registration_state_reader=lambda: {"BAP-MISS-FULLER-VOL01": {"state": "QUALITY_PASSED"}},
    )
    defaults.update(overrides)
    return monitor_state.MonitorState(**defaults)


class TestBasicSnapshot:
    def test_no_active_process_yields_zeroed_safe_defaults(self, tmp_path):
        state = make_state(tmp_path, ps_reader=lambda: PS_IDLE)
        state.poll()
        snap = state.snapshot()
        assert snap["process_alive"] is False
        assert snap["current_source"]["identifier"] is None
        assert snap["processed"] == 0
        assert snap["eta_seconds"] is None
        assert snap["pipeline_stages"] == []

    def test_active_process_reflects_real_report_fields(self, tmp_path):
        _write_report(tmp_path / "tsu", "Fuller_Complete_Works_Vol01",
                       candidates_evaluated=2300, candidates_total=5452,
                       llm_errors=0, elapsed_seconds=26327.06, partial=True)
        state = make_state(tmp_path)
        state.poll()
        snap = state.snapshot()

        assert snap["process_alive"] is True
        assert snap["current_source"]["title"] == "ANDREW FULLER — VOLUME 01"
        assert snap["processed"] == 2300
        assert snap["total"] == 5452
        assert snap["percentage"] == pytest.approx(42.19, abs=0.01)

    def test_poll_never_raises_on_broken_ps_reader(self, tmp_path):
        def boom():
            raise RuntimeError("ps unavailable")

        state = make_state(tmp_path, ps_reader=boom)
        state.poll()
        snap = state.snapshot()
        assert snap["last_poll_ok"] is False

    def test_one_bad_system_reader_does_not_break_tsu_progress_polling(self, tmp_path):
        _write_report(tmp_path / "tsu", "Fuller_Complete_Works_Vol01",
                       candidates_evaluated=10, candidates_total=100)

        def boom():
            raise RuntimeError("ioreg not found")

        state = make_state(tmp_path, gpu_reader=boom)
        state.poll()
        snap = state.snapshot()

        assert snap["system"]["gpu"] is None
        assert snap["processed"] == 10
        assert snap["last_poll_ok"] is True


class TestSystemMetricsAndBottleneck:
    def test_snapshot_includes_system_metrics(self, tmp_path):
        state = make_state(tmp_path)
        state.poll()
        snap = state.snapshot()

        assert snap["system"]["memory"]["percent"] == 60.1
        assert snap["system"]["cpu"]["percent"] == 18.9
        assert snap["system"]["gpu"]["model"] == "Apple M5 Max"
        assert snap["system"]["gpu"]["device_utilization_pct"] == 87
        assert snap["system"]["disk"]["percent"] == 50.0
        assert snap["system"]["thermal_pressure"] == "nominal"
        assert snap["n8n_online"] is True
        assert snap["ollama_models"][0]["name"] == "my-theology-bot-v2:latest"

    def test_bottleneck_reflects_gpu_high_utilization(self, tmp_path):
        state = make_state(tmp_path)  # GPU 87% is the highest known reading
        state.poll()
        snap = state.snapshot()
        assert snap["bottleneck"]["resource"] == "GPU"
        assert "LLM DECODING" in snap["bottleneck"]["label"]

    def test_disk_and_network_rate_is_none_on_first_poll_then_populated(self, tmp_path):
        counters = {"read_bytes": 1000, "write_bytes": 2000}

        def disk_io():
            return counters

        state = make_state(tmp_path, disk_io_reader=disk_io)
        state.poll()
        snap = state.snapshot()
        assert snap["system"]["disk_io_rate"] is None  # no previous sample yet

        counters = {"read_bytes": 3000, "write_bytes": 6000}
        state.poll()
        snap = state.snapshot()
        assert snap["system"]["disk_io_rate"] is not None
        assert snap["system"]["disk_io_rate"]["read_bytes_per_sec"] > 0


class TestPipelineStagesIntegration:
    def test_active_volume_shows_real_pipeline_stage_shape(self, tmp_path):
        tsu_root = tmp_path / "tsu"
        _write_report(tsu_root, "Fuller_Complete_Works_Vol01",
                       candidates_evaluated=2400, candidates_total=5452, partial=True)
        _write_tsu_records(tsu_root, "Fuller_Complete_Works_Vol01", *(["generated"] * 2400))

        state = make_state(tmp_path)
        state.poll()
        snap = state.snapshot()
        by_stage = {s["stage"]: s["status"] for s in snap["pipeline_stages"]}

        assert by_stage["Registration"] == "COMPLETE"
        assert by_stage["TSU Extraction"] == "RUNNING"
        assert by_stage["Quality Gate"] == "BLOCKED"
        assert by_stage["Review"] == "QUEUED"
        assert by_stage["Embedding"] == "QUEUED"
        assert by_stage["Qdrant"] == "QUEUED"


class TestQueueSnapshot:
    def test_active_volume_is_running_others_queued(self, tmp_path):
        _write_report(tmp_path / "tsu", "Fuller_Complete_Works_Vol01",
                       candidates_evaluated=10, candidates_total=100)
        state = make_state(tmp_path)
        state.poll()
        queue = {row["identifier"]: row for row in state.snapshot()["queue"]}

        assert queue["Fuller_Complete_Works_Vol01"]["status"] == "RUNNING"
        assert queue["Fuller_Complete_Works_Vol01"]["progress_pct"] == pytest.approx(10.0)
        assert queue["Fuller_Complete_Works_Vol02"]["status"] == "QUEUED"

    def test_completed_volume_detected_from_report_on_disk(self, tmp_path):
        tsu_root = tmp_path / "tsu"
        _write_report(tsu_root, "Fuller_Complete_Works_Vol01", candidates_evaluated=5452,
                       candidates_total=5452, partial=False)
        _write_report(tsu_root, "Fuller_Complete_Works_Vol02", candidates_evaluated=300,
                       candidates_total=300, partial=False)
        state = make_state(tmp_path, ps_reader=lambda: PS_IDLE)
        state.poll()
        queue = {row["identifier"]: row for row in state.snapshot()["queue"]}
        assert queue["Fuller_Complete_Works_Vol02"]["status"] == "COMPLETE"
        assert queue["Fuller_Complete_Works_Vol02"]["progress_pct"] == 100.0

    def test_failed_volume_detected_from_queue_log(self, tmp_path):
        queue_log = tmp_path / "queue.log"
        queue_log.write_text(
            "[t] starting TSU generation: Fuller_Complete_Works_Vol03\n"
            "[t] Fuller_Complete_Works_Vol03 FAILED (exit=1, partial=True) — STOPPING queue, needs review\n",
            encoding="utf-8",
        )
        (tmp_path / "STOP.md").write_text("# TSU Queue STOP — Fuller_Complete_Works_Vol03\n", encoding="utf-8")
        state = make_state(tmp_path)
        state.poll()
        snap = state.snapshot()
        queue = {row["identifier"]: row for row in snap["queue"]}
        assert queue["Fuller_Complete_Works_Vol03"]["status"] == "FAILED"
        assert snap["queue_stopped"] is True
        assert "Vol03" in snap["queue_stop_reason"]


class TestThroughputAndLatencyHistory:
    def test_history_accumulates_across_polls(self, tmp_path, monkeypatch):
        tsu_root = tmp_path / "tsu"
        _write_report(tsu_root, "Fuller_Complete_Works_Vol01", candidates_evaluated=100,
                       candidates_total=5452, elapsed_seconds=1000.0)
        state = make_state(tmp_path)

        clock = {"t": 1000.0}
        monkeypatch.setattr(monitor_state.time, "time", lambda: clock["t"])

        state.poll()
        clock["t"] += 300
        _write_report(tsu_root, "Fuller_Complete_Works_Vol01", candidates_evaluated=200,
                       candidates_total=5452, elapsed_seconds=1300.0)
        state.poll()

        snap = state.snapshot()
        assert len(snap["throughput_history"]) == 1
        assert snap["throughput_history"][0]["rate_per_hour"] == pytest.approx(1200.0)  # 100 in 300s
        assert len(snap["latency_history"]) == 1
        assert snap["latency_history"][0]["sec_per_item"] == pytest.approx(3.0)  # 300s / 100 items

    def test_system_history_grows_every_poll_not_just_checkpoints(self, tmp_path, monkeypatch):
        state = make_state(tmp_path)
        clock = {"t": 1000.0}
        monkeypatch.setattr(monitor_state.time, "time", lambda: clock["t"])

        state.poll()
        clock["t"] += 5
        state.poll()
        clock["t"] += 5
        state.poll()

        snap = state.snapshot()
        assert len(snap["gpu_history"]) == 3
        assert len(snap["ram_history"]) == 3


class TestEventLogIntegration:
    def test_checkpoint_and_process_transitions_are_logged(self, tmp_path, monkeypatch):
        tsu_root = tmp_path / "tsu"
        _write_report(tsu_root, "Fuller_Complete_Works_Vol01", candidates_evaluated=100, candidates_total=5452)

        clock = {"t": 1000.0}
        monkeypatch.setattr(monitor_state.time, "time", lambda: clock["t"])

        state = make_state(tmp_path)
        state.poll()  # first poll never emits (nothing to diff against)
        assert state.snapshot()["events"] == []

        clock["t"] += 5
        _write_report(tsu_root, "Fuller_Complete_Works_Vol01", candidates_evaluated=200, candidates_total=5452)
        state.poll()

        events = state.snapshot()["events"]
        assert any("checkpoint saved" in e["message"] for e in events)

    def test_process_death_is_logged(self, tmp_path, monkeypatch):
        clock = {"t": 1000.0}
        monkeypatch.setattr(monitor_state.time, "time", lambda: clock["t"])

        ps_state = {"text": PS_ACTIVE_VOL01}
        state = make_state(tmp_path, ps_reader=lambda: ps_state["text"])
        state.poll()

        clock["t"] += 5
        ps_state["text"] = PS_IDLE
        state.poll()

        events = state.snapshot()["events"]
        assert any(e["level"] == "error" and e["message"] == "TSU process stopped" for e in events)


class TestPollLoop:
    def test_start_populates_before_returning_and_stop_joins_thread(self, tmp_path):
        state = make_state(tmp_path)
        loop = monitor_state.PollLoop(state, interval_seconds=0.05)
        loop.start()
        try:
            # start() calls poll() synchronously before spawning the thread.
            assert state.snapshot()["last_poll_ok"] is True
        finally:
            loop.stop()
