"""Tests for the NAE Live Dashboard's read-only state collector
(.automation/night-shift/dashboard/backend/collector.py).

The dashboard backend lives outside the `NAE` package on purpose (it must
never be importable from, or confused with, NAE/pipeline — a Protected
Path). These tests load it by file path and drive it entirely through
tmp_path fixtures and injected ps/ollama callables, so nothing here ever
touches the real NAE/corpus/tsu tree or calls a real subprocess/network
(see memory: test fixtures must override every DEFAULT_*_PATH-style
parameter, never rely on the real path being absent/empty).
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_BACKEND_DIR = Path(__file__).resolve().parents[1] / ".automation" / "night-shift" / "dashboard" / "backend"


def _load_collector():
    spec = importlib.util.spec_from_file_location("nae_dashboard_collector", _BACKEND_DIR / "collector.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


collector = _load_collector()


PS_ACTIVE_VOL01 = (
    "David  88689  0.0  0.0 ...  ??  S  2:29PM  0:03.98 "
    "/opt/homebrew/.../Python -m NAE.pipeline.tsu.runner --identifier Fuller_Complete_Works_Vol01\n"
)
PS_IDLE = "David  123  0.0  0.0 ... some other process\n"


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


class TestPureParsers:
    def test_parse_active_identifier_matches(self):
        assert collector.parse_active_identifier(PS_ACTIVE_VOL01) == "Fuller_Complete_Works_Vol01"

    def test_parse_active_identifier_no_match(self):
        assert collector.parse_active_identifier(PS_IDLE) is None

    def test_volume_title(self):
        assert collector.volume_title("Fuller_Complete_Works_Vol01") == "ANDREW FULLER — VOLUME 01"
        assert collector.volume_title("Fuller_Complete_Works_Vol08") == "ANDREW FULLER — VOLUME 08"

    def test_volume_title_unrecognized_identifier(self):
        assert collector.volume_title("Something_Else") == "ANDREW FULLER — VOLUME ?"

    def test_parse_queue_log(self):
        log = (
            "[t] queue start\n"
            "[t] starting TSU generation: Fuller_Complete_Works_Vol02\n"
            "[t] Fuller_Complete_Works_Vol02 COMPLETE (partial=False)\n"
            "[t] starting TSU generation: Fuller_Complete_Works_Vol03\n"
            "[t] Fuller_Complete_Works_Vol03 FAILED (exit=1, partial=True) — STOPPING queue, needs review\n"
        )
        statuses = collector.parse_queue_log(log)
        assert statuses["Fuller_Complete_Works_Vol02"] == "COMPLETE"
        assert statuses["Fuller_Complete_Works_Vol03"] == "FAILED"

    def test_read_json_safe_missing_file(self, tmp_path):
        assert collector.read_json_safe(tmp_path / "nope.json") is None

    def test_read_json_safe_malformed(self, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text("{not valid json", encoding="utf-8")
        assert collector.read_json_safe(bad) is None

    def test_read_json_safe_valid(self, tmp_path):
        good = tmp_path / "good.json"
        good.write_text(json.dumps({"a": 1}), encoding="utf-8")
        assert collector.read_json_safe(good) == {"a": 1}


class TestMonitorStateSnapshot:
    def _make_state(self, tmp_path, *, ps_text=PS_ACTIVE_VOL01, ollama_online=True):
        return collector.MonitorState(
            tsu_root=tmp_path / "tsu",
            queue_log_path=tmp_path / "queue.log",
            stop_marker_path=tmp_path / "STOP.md",
            ps_reader=lambda: ps_text,
            ollama_checker=lambda: ollama_online,
        )

    def test_no_active_process_yields_zeroed_safe_defaults(self, tmp_path):
        state = self._make_state(tmp_path, ps_text=PS_IDLE)
        state.poll()
        snap = state.snapshot()
        assert snap["process_alive"] is False
        assert snap["current_source"]["identifier"] is None
        assert snap["processed"] == 0
        assert snap["total"] == 0
        assert snap["eta_seconds"] is None

    def test_active_process_reflects_real_report_fields(self, tmp_path):
        tsu_root = tmp_path / "tsu"
        _write_report(
            tsu_root, "Fuller_Complete_Works_Vol01",
            candidates_evaluated=2300, candidates_total=5452,
            llm_errors=0, elapsed_seconds=26327.06, partial=True,
        )
        state = self._make_state(tmp_path)
        state.poll()
        snap = state.snapshot()

        assert snap["process_alive"] is True
        assert snap["ollama_online"] is True
        assert snap["current_source"]["identifier"] == "Fuller_Complete_Works_Vol01"
        assert snap["current_source"]["title"] == "ANDREW FULLER — VOLUME 01"
        assert snap["processed"] == 2300
        assert snap["total"] == 5452
        assert snap["percentage"] == pytest.approx(42.19, abs=0.01)
        assert snap["errors"] == 0
        assert snap["eta_seconds"] is not None and snap["eta_seconds"] > 0

    def test_missing_report_file_does_not_crash(self, tmp_path):
        # Active per ps, but no checkpoint written yet (idx < checkpoint_every).
        state = self._make_state(tmp_path)
        state.poll()
        snap = state.snapshot()
        assert snap["process_alive"] is True
        assert snap["processed"] == 0
        assert snap["total"] == 0

    def test_poll_never_raises_on_broken_ps_reader(self, tmp_path):
        def boom():
            raise RuntimeError("ps unavailable")

        state = collector.MonitorState(
            tsu_root=tmp_path / "tsu",
            queue_log_path=tmp_path / "queue.log",
            stop_marker_path=tmp_path / "STOP.md",
            ps_reader=boom,
            ollama_checker=lambda: False,
        )
        state.poll()  # must not raise
        snap = state.snapshot()
        assert snap["last_poll_ok"] is False

    def test_throughput_history_accumulates_across_polls(self, tmp_path, monkeypatch):
        tsu_root = tmp_path / "tsu"
        _write_report(tsu_root, "Fuller_Complete_Works_Vol01", candidates_evaluated=100, candidates_total=5452)
        state = self._make_state(tmp_path)

        clock = {"t": 1000.0}
        monkeypatch.setattr(collector.time, "time", lambda: clock["t"])

        state.poll()
        clock["t"] += 300
        _write_report(tsu_root, "Fuller_Complete_Works_Vol01", candidates_evaluated=200, candidates_total=5452)
        state.poll()

        snap = state.snapshot()
        assert len(snap["throughput_history"]) == 1
        # 100 candidates in 300s -> 1200/hour
        assert snap["throughput_history"][0]["rate_per_hour"] == pytest.approx(1200.0)


class TestQueueSnapshot:
    def _make_state(self, tmp_path, ps_text=PS_ACTIVE_VOL01):
        return collector.MonitorState(
            tsu_root=tmp_path / "tsu",
            queue_log_path=tmp_path / "queue.log",
            stop_marker_path=tmp_path / "STOP.md",
            ps_reader=lambda: ps_text,
            ollama_checker=lambda: True,
        )

    def test_active_volume_is_running_others_queued(self, tmp_path):
        _write_report(
            tmp_path / "tsu", "Fuller_Complete_Works_Vol01",
            candidates_evaluated=10, candidates_total=100,
        )
        state = self._make_state(tmp_path)
        state.poll()
        queue = {row["identifier"]: row for row in state.snapshot()["queue"]}

        assert queue["Fuller_Complete_Works_Vol01"]["status"] == "RUNNING"
        assert queue["Fuller_Complete_Works_Vol01"]["progress_pct"] == pytest.approx(10.0)
        assert queue["Fuller_Complete_Works_Vol02"]["status"] == "QUEUED"
        assert queue["Fuller_Complete_Works_Vol02"]["progress_pct"] == 0.0

    def test_completed_volume_detected_from_report_on_disk(self, tmp_path):
        tsu_root = tmp_path / "tsu"
        _write_report(tsu_root, "Fuller_Complete_Works_Vol01", candidates_evaluated=5452,
                       candidates_total=5452, partial=False)
        # Vol02 finished a prior run and is sitting on disk with partial=False,
        # even though the runner has moved on (not in ps output).
        _write_report(tsu_root, "Fuller_Complete_Works_Vol02", candidates_evaluated=300,
                       candidates_total=300, partial=False)
        state = self._make_state(tmp_path, ps_text=PS_IDLE)
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
        state = self._make_state(tmp_path)
        state.poll()
        snap = state.snapshot()
        queue = {row["identifier"]: row for row in snap["queue"]}
        assert queue["Fuller_Complete_Works_Vol03"]["status"] == "FAILED"
        assert snap["queue_stopped"] is True
        assert "Vol03" in snap["queue_stop_reason"]


# Real `ioreg -r -d 1 -c IOAccelerator` output is not JSON — a captured,
# trimmed sample of the actual property-list-style text (Apple M5 Max).
SAMPLE_IOREG_TEXT = (
    '+-o AGXAcceleratorG17X  <class AGXAcceleratorG17X, id 0x1000006f7, registered>\n'
    '    {\n'
    '      "PerformanceStatistics" = {"In use system memory (driver)"=0,'
    '"Renderer Utilization %"=8,"Device Utilization %"=87,'
    '"In use system memory"=54969483264}\n'
    '      "model" = "Apple M5 Max"\n'
    '      "gpu-core-count" = 40\n'
    '    }\n'
)

SAMPLE_OLLAMA_PS = {
    "models": [
        {
            "name": "my-theology-bot-v2:latest",
            "size": 53493230468,
            "size_vram": 53493230468,
            "details": {"parameter_size": "70.6B", "quantization_level": "Q4_K_M"},
            "context_length": 32768,
            "expires_at": "2026-08-16T22:24:12.859989-05:00",
        },
    ],
}


class TestGpuAndOllamaModelParsers:
    def test_parse_gpu_stats_from_real_shaped_ioreg_text(self):
        gpu = collector.parse_gpu_stats(SAMPLE_IOREG_TEXT)
        assert gpu == {
            "model": "Apple M5 Max",
            "core_count": 40,
            "device_utilization_pct": 87,
            "in_use_memory_bytes": 54969483264,
        }

    def test_parse_gpu_stats_returns_none_when_no_accelerator(self):
        assert collector.parse_gpu_stats("") is None
        assert collector.parse_gpu_stats("no matching fields here") is None

    def test_parse_ollama_models(self):
        models = collector.parse_ollama_models(SAMPLE_OLLAMA_PS)
        assert len(models) == 1
        assert models[0]["name"] == "my-theology-bot-v2:latest"
        assert models[0]["size_vram_bytes"] == 53493230468
        assert models[0]["parameter_size"] == "70.6B"
        assert models[0]["quantization"] == "Q4_K_M"

    def test_parse_ollama_models_empty(self):
        assert collector.parse_ollama_models({}) == []
        assert collector.parse_ollama_models(None) == []


class TestMonitorStateSystemMetrics:
    def _make_state(self, tmp_path, **overrides):
        defaults = dict(
            tsu_root=tmp_path / "tsu",
            queue_log_path=tmp_path / "queue.log",
            stop_marker_path=tmp_path / "STOP.md",
            ps_reader=lambda: PS_ACTIVE_VOL01,
            ollama_checker=lambda: True,
            memory_reader=lambda: {"total_bytes": 137438953472, "used_bytes": 82696290304,
                                    "available_bytes": 23069376512, "percent": 83.2},
            cpu_reader=lambda: {"percent": 18.9, "core_count": 18, "load_avg_1m": 8.5},
            gpu_reader=lambda: SAMPLE_IOREG_TEXT,
            ollama_models_reader=lambda: collector.parse_ollama_models(SAMPLE_OLLAMA_PS),
        )
        defaults.update(overrides)
        return collector.MonitorState(**defaults)

    def test_snapshot_includes_system_metrics(self, tmp_path):
        state = self._make_state(tmp_path)
        state.poll()
        snap = state.snapshot()

        assert snap["system"]["memory"]["percent"] == 83.2
        assert snap["system"]["cpu"]["percent"] == 18.9
        assert snap["system"]["gpu"]["model"] == "Apple M5 Max"
        assert snap["system"]["gpu"]["device_utilization_pct"] == 87
        assert snap["ollama_models"][0]["name"] == "my-theology-bot-v2:latest"

    def test_one_bad_system_reader_does_not_break_tsu_progress_polling(self, tmp_path):
        """A GPU reader failure (e.g. ioreg absent on non-Apple hardware)
        must not prevent processed/total from updating — these are
        independent, best-effort reads bundled in the same poll cycle."""
        _write_report(tmp_path / "tsu", "Fuller_Complete_Works_Vol01",
                       candidates_evaluated=10, candidates_total=100)

        def boom():
            raise RuntimeError("ioreg not found")

        state = self._make_state(tmp_path, gpu_reader=boom)
        state.poll()
        snap = state.snapshot()

        assert snap["system"]["gpu"] is None
        assert snap["processed"] == 10
        assert snap["total"] == 100
        assert snap["last_poll_ok"] is True

    def test_missing_system_metrics_default_to_none_before_first_poll(self, tmp_path):
        state = self._make_state(tmp_path)
        snap = state.snapshot()
        assert snap["system"]["memory"] is None
        assert snap["system"]["cpu"] is None
        assert snap["system"]["gpu"] is None
        assert snap["ollama_models"] == []
