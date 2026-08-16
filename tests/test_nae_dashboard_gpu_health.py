"""Tests for gpu_health.py — utilization alone must never drive the
verdict; only the thermal-warning signal (or its absence) does."""
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


gpu_health = _load("gpu_health")

HIGH_UTIL_GPU = {"model": "Apple M5 Max", "core_count": 40, "device_utilization_pct": 99,
                  "in_use_memory_bytes": 54000000000}
LOW_UTIL_GPU = {"model": "Apple M5 Max", "core_count": 40, "device_utilization_pct": 2,
                 "in_use_memory_bytes": 1000000}


def test_no_gpu_stats_is_unknown():
    result = gpu_health.compute_gpu_health(gpu_stats=None, thermal_pressure="nominal")
    assert result["status"] == "UNKNOWN"


def test_high_utilization_with_nominal_thermal_is_healthy():
    """This is the real, current Fuller Vol.1 situation: 99% GPU
    utilization, no thermal warning — must be HEALTHY, not WARNING."""
    result = gpu_health.compute_gpu_health(gpu_stats=HIGH_UTIL_GPU, thermal_pressure="nominal")
    assert result["status"] == "HEALTHY"
    assert result["thermal_throttle"] == "NO"


def test_low_utilization_is_not_automatically_healthier():
    """Utilization must never be part of the judgment either way."""
    result = gpu_health.compute_gpu_health(gpu_stats=LOW_UTIL_GPU, thermal_pressure="nominal")
    assert result["status"] == "HEALTHY"


def test_elevated_thermal_is_warning_regardless_of_utilization():
    high = gpu_health.compute_gpu_health(gpu_stats=HIGH_UTIL_GPU, thermal_pressure="elevated")
    low = gpu_health.compute_gpu_health(gpu_stats=LOW_UTIL_GPU, thermal_pressure="elevated")
    assert high["status"] == "WARNING"
    assert low["status"] == "WARNING"
    assert high["thermal_throttle"] == "YES"


def test_unknown_thermal_reading_still_reports_healthy_with_unknown_throttle():
    result = gpu_health.compute_gpu_health(gpu_stats=HIGH_UTIL_GPU, thermal_pressure="unknown")
    assert result["status"] == "HEALTHY"
    assert result["thermal_throttle"] == "UNKNOWN"


def test_xid_and_power_throttle_are_always_unavailable_signals():
    """No Apple Silicon equivalent exists for either — never fabricated."""
    for thermal in ("nominal", "elevated", "unknown"):
        result = gpu_health.compute_gpu_health(gpu_stats=HIGH_UTIL_GPU, thermal_pressure=thermal)
        assert result["xid_errors"] is None
        assert result["power_throttle"] == "UNKNOWN"
