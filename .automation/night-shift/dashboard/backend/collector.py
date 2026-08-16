"""NAE Live Dashboard — read-only IO layer.

Every function here is either a raw IO boundary (subprocess/psutil/HTTP
GET/file read) or a pure parser next to the boundary it parses. Nothing
in this module holds state, polls on a timer, or computes a judgment —
that orchestration lives in monitor_state.py (MonitorState/PollLoop),
which calls these functions from a background thread and caches the
results so request handlers never block on IO.

Observes the existing Fuller TSU extraction production run (`NAE.pipeline.
tsu.runner`, PID managed elsewhere) purely by reading files it already
writes (`tsu_report.json`, `tsu_id_state.json`), the queue log written by
`.automation/night-shift/run_tsu_queue.sh`, `ps aux` output, Ollama's own
health/`/api/ps` endpoints, and n8n's `/healthz`. System resource
visibility (memory/CPU via psutil, Apple Silicon GPU via `ioreg`, thermal
pressure via `pmset -g therm` — none require sudo) is read the same way:
OS/kernel counters and IORegistry queries, never a write.

This module performs NO writes to any NAE/production path and sends NO
commands to any process — it only reads. Mirrors the same read set as
`.automation/night-shift/hourly_check.sh` (active_identifier via ps grep,
tsu_report.json fields), so the dashboard and the CUE monitoring sidecar
never disagree about what "progress" means.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

import psutil
import requests

REPO_ROOT = Path(__file__).resolve().parents[4]
TSU_ROOT = REPO_ROOT / "NAE" / "corpus" / "tsu"
NIGHT_SHIFT_EVIDENCE = REPO_ROOT / ".automation" / "evidence" / "night-shift" / "tsu-processing-connection"
QUEUE_LOG_PATH = NIGHT_SHIFT_EVIDENCE / "queue-vol02-08.log"
STOP_MARKER_PATH = NIGHT_SHIFT_EVIDENCE / "STOP.md"
REGISTRATION_STATE_PATH = REPO_ROOT / "NAE" / "pipeline" / "registration" / "state" / "registration_state.json"
OLLAMA_HEALTH_URL = "http://127.0.0.1:11434/api/version"
OLLAMA_PS_URL = "http://127.0.0.1:11434/api/ps"
N8N_HEALTH_URL = "http://127.0.0.1:5678/healthz"

# Mirrors run_tsu_queue.sh's VOLUMES list (Vol02-08) with Vol01 prepended —
# Vol01 was launched separately, before the queue script existed.
VOLUME_QUEUE: list[str] = [f"Fuller_Complete_Works_Vol{n:02d}" for n in range(1, 9)]

_RUNNER_PATTERN = re.compile(r"NAE\.pipeline\.tsu\.runner --identifier (Fuller_Complete_Works_Vol\d+)")
_VOLUME_NUM_PATTERN = re.compile(r"Vol(\d+)$")
_QUEUE_START_PATTERN = re.compile(r"starting TSU generation: (Fuller_Complete_Works_Vol\d+)")
_QUEUE_COMPLETE_PATTERN = re.compile(r"(Fuller_Complete_Works_Vol\d+) COMPLETE \(partial=False\)")
_QUEUE_FAILED_PATTERN = re.compile(r"(Fuller_Complete_Works_Vol\d+) FAILED")

# Apple Silicon GPU stats parsed out of ioreg's IOAccelerator node text
# (not JSON — ioreg has no -j/--json mode for property dumps).
_GPU_UTIL_PATTERN = re.compile(r'"Device Utilization %"\s*=\s*(\d+)')
_GPU_MEM_PATTERN = re.compile(r'"In use system memory"\s*=\s*(\d+)')
_GPU_MODEL_PATTERN = re.compile(r'"model"\s*=\s*"([^"]*)"')
_GPU_CORES_PATTERN = re.compile(r'"gpu-core-count"\s*=\s*(\d+)')

# One llama-server process per loaded model (see ps aux); `-np N` is its
# actual concurrency setting, read straight off its own command line.
_LLAMA_SERVER_NP_PATTERN = re.compile(r"llama-server.*-np (\d+)")


def read_ps_aux() -> str:
    """IO boundary — real `ps aux` call. Read-only; sends no signal to any process."""
    try:
        result = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=5)
        return result.stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def check_ollama_online(timeout: float = 1.5) -> bool:
    """IO boundary — GET only, Ollama's own health endpoint."""
    try:
        resp = requests.get(OLLAMA_HEALTH_URL, timeout=timeout)
        return resp.status_code == 200
    except requests.RequestException:
        return False


def check_n8n_online(timeout: float = 1.5) -> bool:
    """IO boundary — GET only, n8n's own /healthz (lighter than hitting
    the app's root HTML on every 5s poll)."""
    try:
        resp = requests.get(N8N_HEALTH_URL, timeout=timeout)
        return resp.status_code == 200
    except requests.RequestException:
        return False


def parse_llama_server_parallelism(ps_text: str) -> list[int]:
    return [int(n) for n in _LLAMA_SERVER_NP_PATTERN.findall(ps_text)]


def read_disk_usage(path: Path = REPO_ROOT) -> dict:
    """IO boundary — psutil reads the filesystem's own statvfs counters."""
    du = psutil.disk_usage(str(path))
    return {"total_bytes": du.total, "used_bytes": du.used, "percent": du.percent}


def read_disk_io_raw() -> dict | None:
    """Cumulative byte counters since boot — the caller derives a rate
    from the delta between two samples, same pattern as throughput."""
    counters = psutil.disk_io_counters()
    if counters is None:
        return None
    return {"read_bytes": counters.read_bytes, "write_bytes": counters.write_bytes}


def read_net_io_raw() -> dict | None:
    counters = psutil.net_io_counters()
    if counters is None:
        return None
    return {"bytes_sent": counters.bytes_sent, "bytes_recv": counters.bytes_recv}


def read_thermal_pressure_raw(timeout: float = 3.0) -> str:
    """IO boundary — `pmset -g therm` reports the OS's own recorded
    thermal *warning* flag, not a numeric temperature. Real Celsius/Watts
    figures require `powermetrics`, which needs sudo — deliberately not
    used anywhere in this dashboard (see CLAUDE.md Production 보호 원칙:
    never elevate privileges, never touch anything that could affect the
    running Ollama process)."""
    try:
        result = subprocess.run(["pmset", "-g", "therm"], capture_output=True, text=True, timeout=timeout)
        return result.stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def parse_thermal_pressure(pmset_text: str) -> str:
    """Returns 'nominal' | 'elevated' | 'unknown'. Coarse on purpose —
    this is the only sudo-free thermal signal macOS exposes."""
    if not pmset_text:
        return "unknown"
    if "No thermal warning level has been recorded" in pmset_text:
        return "nominal"
    return "elevated"


def read_gpu_stats_raw(timeout: float = 3.0) -> str:
    """IO boundary — `ioreg -r -d 1 -c IOAccelerator` only *inspects* the
    IORegistry (read-only query flags: -r restrict to matches, -d 1 one
    level deep, -c the class name). No sudo required, unlike powermetrics.
    Sends no command to the GPU."""
    try:
        result = subprocess.run(
            ["ioreg", "-r", "-d", "1", "-c", "IOAccelerator"],
            capture_output=True, text=True, timeout=timeout,
        )
        return result.stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def parse_gpu_stats(ioreg_text: str) -> dict | None:
    """Apple Silicon only. Returns None if the expected fields aren't
    present (e.g. non-Apple-GPU hardware, or ioreg output shape changes)."""
    util = _GPU_UTIL_PATTERN.search(ioreg_text)
    if util is None:
        return None
    mem = _GPU_MEM_PATTERN.search(ioreg_text)
    model = _GPU_MODEL_PATTERN.search(ioreg_text)
    cores = _GPU_CORES_PATTERN.search(ioreg_text)
    return {
        "model": model.group(1) if model else None,
        "core_count": int(cores.group(1)) if cores else None,
        "device_utilization_pct": int(util.group(1)),
        "in_use_memory_bytes": int(mem.group(1)) if mem else None,
    }


def read_system_memory() -> dict:
    """IO boundary — psutil reads /proc-equivalent OS counters, no writes."""
    vm = psutil.virtual_memory()
    return {
        "total_bytes": vm.total,
        "used_bytes": vm.used,
        "available_bytes": vm.available,
        "percent": vm.percent,
    }


def read_cpu_stats() -> dict:
    """IO boundary. `cpu_percent(interval=None)` is non-blocking — it
    compares against the last call, which is exactly right for a poll
    loop that calls this every few seconds anyway."""
    try:
        load1, _load5, _load15 = os.getloadavg()
    except (OSError, AttributeError):
        load1 = None
    return {
        "percent": psutil.cpu_percent(interval=None),
        "core_count": psutil.cpu_count(logical=True),
        "load_avg_1m": load1,
    }


def read_ollama_ps_raw(timeout: float = 1.5) -> dict:
    """IO boundary — GET /api/ps, Ollama's own "what's currently loaded"
    endpoint. Read-only (no /api/generate, /api/pull, /api/delete, etc.)."""
    try:
        resp = requests.get(OLLAMA_PS_URL, timeout=timeout)
        if resp.status_code != 200:
            return {}
        return resp.json()
    except (requests.RequestException, ValueError):
        return {}


def parse_ollama_models(data: dict) -> list[dict]:
    models = []
    for m in (data or {}).get("models", []):
        details = m.get("details") or {}
        models.append({
            "name": m.get("name"),
            "size_bytes": m.get("size"),
            "size_vram_bytes": m.get("size_vram"),
            "parameter_size": details.get("parameter_size"),
            "quantization": details.get("quantization_level"),
            "context_length": m.get("context_length"),
            "expires_at": m.get("expires_at"),
        })
    return models


def read_ollama_models(timeout: float = 1.5) -> list[dict]:
    return parse_ollama_models(read_ollama_ps_raw(timeout))


def parse_active_identifier(ps_text: str) -> str | None:
    match = _RUNNER_PATTERN.search(ps_text)
    return match.group(1) if match else None


def read_json_safe(path: Path) -> dict | list | None:
    """Tolerates a concurrent checkpoint write (builder.py rewrites this file
    every 100 candidates) — a transient parse failure just keeps the last
    known-good value in the caller, it never raises."""
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None


def read_registration_state(path: Path = REGISTRATION_STATE_PATH) -> dict:
    """source_id -> {state, updated_at} map written by
    NAE/pipeline/registration/state.py::RegistrationStateStore."""
    data = read_json_safe(path)
    return data if isinstance(data, dict) else {}


def read_index_report(tsu_root: Path, identifier: str) -> dict | None:
    """NAE/pipeline/index/indexer.py writes index_report.json to the same
    per-identifier directory as tsu_report.json — cheap to check, no
    tree-wide search needed."""
    data = read_json_safe(tsu_root / identifier / "index_report.json")
    return data if isinstance(data, dict) else None


def volume_title(identifier: str) -> str:
    match = _VOLUME_NUM_PATTERN.search(identifier)
    num = match.group(1) if match else "?"
    return f"ANDREW FULLER — VOLUME {num}"


def parse_queue_log(log_text: str) -> dict[str, str]:
    """{identifier: 'RUNNING' | 'COMPLETE' | 'FAILED'} from queue-vol02-08.log lines."""
    statuses: dict[str, str] = {}
    for line in log_text.splitlines():
        m = _QUEUE_START_PATTERN.search(line)
        if m:
            statuses[m.group(1)] = "RUNNING"
        m = _QUEUE_COMPLETE_PATTERN.search(line)
        if m:
            statuses[m.group(1)] = "COMPLETE"
        m = _QUEUE_FAILED_PATTERN.search(line)
        if m:
            statuses[m.group(1)] = "FAILED"
    return statuses

