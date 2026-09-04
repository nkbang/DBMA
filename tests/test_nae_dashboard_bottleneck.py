"""Tests for bottleneck.py — deterministic, threshold-based, UNKNOWN when
readings are missing (never a guess)."""
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


bottleneck = _load("bottleneck")


def test_unknown_when_all_readings_missing():
    result = bottleneck.compute_bottleneck(gpu_pct=None, cpu_pct=None, ram_pct=None, ollama_active=False)
    assert result["resource"] == "UNKNOWN"


def test_judges_on_whatever_readings_are_known_when_one_is_missing():
    """GPU missing but CPU/RAM known and both low -> judge on the known
    ones rather than refusing to answer at all."""
    result = bottleneck.compute_bottleneck(gpu_pct=None, cpu_pct=10.0, ram_pct=20.0, ollama_active=False)
    assert result["resource"] == "NONE"  # known readings are all below threshold


def test_none_when_all_below_threshold():
    result = bottleneck.compute_bottleneck(gpu_pct=40.0, cpu_pct=20.0, ram_pct=60.0, ollama_active=True)
    assert result["resource"] == "NONE"


def test_gpu_bottleneck_with_ollama_active_labels_llm_decoding():
    result = bottleneck.compute_bottleneck(gpu_pct=99.0, cpu_pct=15.0, ram_pct=80.0, ollama_active=True)
    assert result["resource"] == "GPU"
    assert result["label"] == "GPU / LLM DECODING"


def test_gpu_bottleneck_without_ollama_active_plain_label():
    result = bottleneck.compute_bottleneck(gpu_pct=90.0, cpu_pct=15.0, ram_pct=80.0, ollama_active=False)
    assert result["resource"] == "GPU"
    assert result["label"] == "GPU"


def test_cpu_bottleneck_when_cpu_highest():
    result = bottleneck.compute_bottleneck(gpu_pct=10.0, cpu_pct=95.0, ram_pct=50.0, ollama_active=False)
    assert result["resource"] == "CPU"


def test_ram_bottleneck_when_ram_highest():
    result = bottleneck.compute_bottleneck(gpu_pct=10.0, cpu_pct=20.0, ram_pct=92.0, ollama_active=False)
    assert result["resource"] == "RAM"


def test_exactly_at_threshold_counts_as_bottleneck():
    result = bottleneck.compute_bottleneck(gpu_pct=85.0, cpu_pct=0.0, ram_pct=0.0, ollama_active=False,
                                            threshold=85.0)
    assert result["resource"] == "GPU"
