"""NAE Live Dashboard — read-only state collector.

Observes the existing Fuller TSU extraction production run (`NAE.pipeline.
tsu.runner`, PID managed elsewhere) purely by reading files it already
writes (`tsu_report.json`, `tsu_id_state.json`), the queue log written by
`.automation/night-shift/run_tsu_queue.sh`, `ps aux` output, and Ollama's
own health/`/api/ps` endpoints. System resource visibility (memory/CPU via
psutil, Apple Silicon GPU via `ioreg` — no sudo required) is read the same
way: OS/kernel counters and IORegistry queries, never a write.

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
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import psutil
import requests

REPO_ROOT = Path(__file__).resolve().parents[4]
TSU_ROOT = REPO_ROOT / "NAE" / "corpus" / "tsu"
NIGHT_SHIFT_EVIDENCE = REPO_ROOT / ".automation" / "evidence" / "night-shift" / "tsu-processing-connection"
QUEUE_LOG_PATH = NIGHT_SHIFT_EVIDENCE / "queue-vol02-08.log"
STOP_MARKER_PATH = NIGHT_SHIFT_EVIDENCE / "STOP.md"
OLLAMA_HEALTH_URL = "http://127.0.0.1:11434/api/version"
OLLAMA_PS_URL = "http://127.0.0.1:11434/api/ps"

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


def _safe(reader: Callable[[], object], default: object):
    """A slow/unavailable system-metrics reader (psutil hiccup, ioreg
    absent on non-Apple hardware, Ollama briefly unreachable) must not
    knock out the TSU progress read it's bundled with in the same poll
    cycle — each of these is independently best-effort."""
    try:
        return reader()
    except Exception:
        return default


@dataclass
class ThroughputSample:
    ts: float
    evaluated: int


@dataclass
class _ActiveState:
    active: str | None = None
    process_alive: bool = False
    ollama_online: bool = False
    last_poll_ts: float | None = None
    last_poll_ok: bool = False
    memory: dict | None = None
    cpu: dict | None = None
    gpu: dict | None = None
    ollama_models: list = field(default_factory=list)


class MonitorState:
    """Background-polled, read-only view of the current TSU extraction run.

    `poll()` is meant to be called on a timer from a background thread;
    `snapshot()` is safe to call from request handlers at any time and
    never blocks on IO.
    """

    def __init__(
        self,
        *,
        tsu_root: Path = TSU_ROOT,
        queue_log_path: Path = QUEUE_LOG_PATH,
        stop_marker_path: Path = STOP_MARKER_PATH,
        history_window_seconds: float = 3600.0,
        ps_reader: Callable[[], str] = read_ps_aux,
        ollama_checker: Callable[[], bool] = check_ollama_online,
        memory_reader: Callable[[], dict] = read_system_memory,
        cpu_reader: Callable[[], dict] = read_cpu_stats,
        gpu_reader: Callable[[], str] = read_gpu_stats_raw,
        ollama_models_reader: Callable[[], list] = read_ollama_models,
    ) -> None:
        self._tsu_root = tsu_root
        self._queue_log_path = queue_log_path
        self._stop_marker_path = stop_marker_path
        self._history_window = history_window_seconds
        self._ps_reader = ps_reader
        self._ollama_checker = ollama_checker
        self._memory_reader = memory_reader
        self._cpu_reader = cpu_reader
        self._gpu_reader = gpu_reader
        self._ollama_models_reader = ollama_models_reader

        self._lock = threading.Lock()
        self._state = _ActiveState()
        self._reports: dict[str, dict] = {}
        self._history: dict[str, deque[ThroughputSample]] = {}

    def poll(self) -> None:
        """One read cycle. Never raises — a failed poll just leaves the
        previous snapshot in place so the dashboard degrades gracefully
        instead of going blank."""
        try:
            ps_text = self._ps_reader()
            active = parse_active_identifier(ps_text)
            ollama_online = self._ollama_checker()
            memory = _safe(self._memory_reader, None)
            cpu = _safe(self._cpu_reader, None)
            gpu = _safe(lambda: parse_gpu_stats(self._gpu_reader()), None)
            ollama_models = _safe(self._ollama_models_reader, [])

            report = None
            if active:
                report = read_json_safe(self._tsu_root / active / "tsu_report.json")

            now = time.time()
            with self._lock:
                self._state.active = active
                self._state.process_alive = active is not None
                self._state.ollama_online = ollama_online
                self._state.memory = memory
                self._state.cpu = cpu
                self._state.gpu = gpu
                self._state.ollama_models = ollama_models
                self._state.last_poll_ts = now
                self._state.last_poll_ok = True
                if active and report is not None:
                    self._reports[active] = report
                    hist = self._history.setdefault(active, deque())
                    hist.append(ThroughputSample(ts=now, evaluated=report.get("candidates_evaluated", 0)))
                    cutoff = now - self._history_window
                    while hist and hist[0].ts < cutoff:
                        hist.popleft()
        except Exception:
            with self._lock:
                self._state.last_poll_ts = time.time()
                self._state.last_poll_ok = False

    def _queue_snapshot(self, active: str | None) -> tuple[list[dict], bool, str | None]:
        log_text = ""
        try:
            log_text = self._queue_log_path.read_text(encoding="utf-8")
        except OSError:
            pass
        queue_statuses = parse_queue_log(log_text)

        stopped = self._stop_marker_path.exists()
        stop_reason = None
        if stopped:
            try:
                stop_reason = self._stop_marker_path.read_text(encoding="utf-8").strip().splitlines()[0]
            except (OSError, IndexError):
                stop_reason = "STOP.md present"

        entries = []
        for vol in VOLUME_QUEUE:
            if vol == active:
                report = self._reports.get(vol, {})
                total = report.get("candidates_total") or 0
                evaluated = report.get("candidates_evaluated") or 0
                pct = round(100 * evaluated / total, 1) if total else 0.0
                entries.append({"identifier": vol, "status": "RUNNING", "progress_pct": pct})
                continue

            on_disk = read_json_safe(self._tsu_root / vol / "tsu_report.json")
            if isinstance(on_disk, dict) and on_disk.get("partial") is False:
                entries.append({"identifier": vol, "status": "COMPLETE", "progress_pct": 100.0})
                continue

            logged = queue_statuses.get(vol)
            if logged == "FAILED":
                entries.append({"identifier": vol, "status": "FAILED", "progress_pct": 0.0})
            elif logged == "COMPLETE":
                entries.append({"identifier": vol, "status": "COMPLETE", "progress_pct": 100.0})
            elif logged == "RUNNING":
                entries.append({"identifier": vol, "status": "RUNNING", "progress_pct": 0.0})
            else:
                entries.append({"identifier": vol, "status": "QUEUED", "progress_pct": 0.0})

        return entries, stopped, stop_reason

    def snapshot(self) -> dict:
        with self._lock:
            active = self._state.active
            process_alive = self._state.process_alive
            ollama_online = self._state.ollama_online
            last_poll_ts = self._state.last_poll_ts
            last_poll_ok = self._state.last_poll_ok
            memory = dict(self._state.memory) if self._state.memory else None
            cpu = dict(self._state.cpu) if self._state.cpu else None
            gpu = dict(self._state.gpu) if self._state.gpu else None
            ollama_models = list(self._state.ollama_models)
            report = dict(self._reports.get(active, {})) if active else None
            history = list(self._history.get(active, [])) if active else []

        processed = report.get("candidates_evaluated", 0) if report else 0
        total = report.get("candidates_total", 0) if report else 0
        errors = report.get("llm_errors", 0) if report else 0
        elapsed = report.get("elapsed_seconds", 0.0) if report else 0.0
        percentage = round(100 * processed / total, 2) if total else 0.0

        avg_rate_per_sec = (processed / elapsed) if elapsed > 0 else 0.0
        throughput_per_hour = round(avg_rate_per_sec * 3600, 1)
        sec_per_item = round(elapsed / processed, 2) if processed > 0 else None
        remaining = max(total - processed, 0)
        eta_seconds = round(remaining / avg_rate_per_sec, 0) if avg_rate_per_sec > 0 else None

        sparkline = []
        for prev, cur in zip(history, history[1:]):
            dt = cur.ts - prev.ts
            d_ev = cur.evaluated - prev.evaluated
            rate_per_hour = (d_ev / dt * 3600) if dt > 0 else 0.0
            sparkline.append({"t": cur.ts, "rate_per_hour": round(rate_per_hour, 1)})

        queue, queue_stopped, stop_reason = self._queue_snapshot(active)

        return {
            "current_source": {
                "identifier": active,
                "title": volume_title(active) if active else None,
            },
            "processed": processed,
            "total": total,
            "percentage": percentage,
            "throughput_per_hour": throughput_per_hour,
            "sec_per_item": sec_per_item,
            "eta_seconds": eta_seconds,
            "errors": errors,
            "elapsed_seconds": elapsed,
            "process_alive": process_alive,
            "ollama_online": ollama_online,
            "system": {
                "memory": memory,
                "cpu": cpu,
                "gpu": gpu,
            },
            "ollama_models": ollama_models,
            "queue": queue,
            "queue_stopped": queue_stopped,
            "queue_stop_reason": stop_reason,
            "throughput_history": sparkline,
            "last_poll_at": last_poll_ts,
            "last_poll_ok": last_poll_ok,
            "server_time": time.time(),
        }


class PollLoop:
    """Owns the background thread that calls MonitorState.poll() on a timer."""

    def __init__(self, state: MonitorState, interval_seconds: float = 5.0) -> None:
        self._state = state
        self._interval = interval_seconds
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None:
            return
        self._state.poll()  # populate before first request
        self._thread = threading.Thread(target=self._run, name="nae-dashboard-poll", daemon=True)
        self._thread.start()

    def _run(self) -> None:
        while not self._stop.is_set():
            self._stop.wait(self._interval)
            if self._stop.is_set():
                break
            self._state.poll()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2)
