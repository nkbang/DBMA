"""Tests for the NAE Live Dashboard's read-only IO layer
(.automation/night-shift/dashboard/backend/collector.py) — pure parsers
and file-read boundaries only. MonitorState/PollLoop orchestration tests
live in test_nae_dashboard_monitor_state.py (that class moved to
monitor_state.py).

The dashboard backend lives outside the `NAE` package on purpose (it must
never be importable from, or confused with, NAE/pipeline — a Protected
Path). These tests load it by file path and drive it entirely through
tmp_path fixtures, so nothing here ever touches the real NAE/corpus/tsu
tree or calls a real subprocess/network (see memory: test fixtures must
override every DEFAULT_*_PATH-style parameter, never rely on the real
path being absent/empty).
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

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
PS_TWO_LLAMA_SERVERS = (
    "David  76935  ... llama-server --model a --port 62286 ... -np 1 ...\n"
    "David  76993  ... llama-server --model b --port 62419 ... -np 4 ...\n"
)


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

    def test_parse_llama_server_parallelism(self):
        assert collector.parse_llama_server_parallelism(PS_TWO_LLAMA_SERVERS) == [1, 4]
        assert collector.parse_llama_server_parallelism(PS_IDLE) == []

    def test_parse_thermal_pressure_nominal(self):
        assert collector.parse_thermal_pressure(
            "Note: No thermal warning level has been recorded\n"
        ) == "nominal"

    def test_parse_thermal_pressure_elevated_when_warning_present(self):
        assert collector.parse_thermal_pressure(
            "CPU_Scheduler_Limit\tthermalState = 2\n"
        ) == "elevated"

    def test_parse_thermal_pressure_unknown_when_empty(self):
        assert collector.parse_thermal_pressure("") == "unknown"


class TestRegistrationAndIndexReportReaders:
    def test_read_registration_state_missing_file_returns_empty_dict(self, tmp_path):
        assert collector.read_registration_state(tmp_path / "nope.json") == {}

    def test_read_registration_state_reads_real_shape(self, tmp_path):
        path = tmp_path / "registration_state.json"
        path.write_text(json.dumps({"BAP-MISS-FULLER-VOL01": {"state": "QUALITY_PASSED"}}), encoding="utf-8")
        state = collector.read_registration_state(path)
        assert state["BAP-MISS-FULLER-VOL01"]["state"] == "QUALITY_PASSED"

    def test_read_index_report_missing_returns_none(self, tmp_path):
        assert collector.read_index_report(tmp_path, "Fuller_Complete_Works_Vol01") is None

    def test_read_index_report_reads_real_shape(self, tmp_path):
        out_dir = tmp_path / "Fuller_Complete_Works_Vol01"
        out_dir.mkdir(parents=True)
        (out_dir / "index_report.json").write_text(json.dumps({"indexed": 5}), encoding="utf-8")
        report = collector.read_index_report(tmp_path, "Fuller_Complete_Works_Vol01")
        assert report == {"indexed": 5}


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
