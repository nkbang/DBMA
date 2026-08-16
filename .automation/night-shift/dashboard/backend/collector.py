"""NAE Live Dashboard — read-only state collector.

Observes the existing Fuller TSU extraction production run (`NAE.pipeline.
tsu.runner`, PID managed elsewhere) purely by reading files it already
writes (`tsu_report.json`, `tsu_id_state.json`), the queue log written by
`.automation/night-shift/run_tsu_queue.sh`, `ps aux` output, and Ollama's
own health endpoint.

This module performs NO writes to any NAE/production path and sends NO
commands to any process — it only reads. Mirrors the same read set as
`.automation/night-shift/hourly_check.sh` (active_identifier via ps grep,
tsu_report.json fields), so the dashboard and the CUE monitoring sidecar
never disagree about what "progress" means.
"""
from __future__ import annotations

import json
import re
import subprocess
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import requests

REPO_ROOT = Path(__file__).resolve().parents[4]
TSU_ROOT = REPO_ROOT / "NAE" / "corpus" / "tsu"
NIGHT_SHIFT_EVIDENCE = REPO_ROOT / ".automation" / "evidence" / "night-shift" / "tsu-processing-connection"
QUEUE_LOG_PATH = NIGHT_SHIFT_EVIDENCE / "queue-vol02-08.log"
STOP_MARKER_PATH = NIGHT_SHIFT_EVIDENCE / "STOP.md"
OLLAMA_HEALTH_URL = "http://127.0.0.1:11434/api/version"

# Mirrors run_tsu_queue.sh's VOLUMES list (Vol02-08) with Vol01 prepended —
# Vol01 was launched separately, before the queue script existed.
VOLUME_QUEUE: list[str] = [f"Fuller_Complete_Works_Vol{n:02d}" for n in range(1, 9)]

_RUNNER_PATTERN = re.compile(r"NAE\.pipeline\.tsu\.runner --identifier (Fuller_Complete_Works_Vol\d+)")
_VOLUME_NUM_PATTERN = re.compile(r"Vol(\d+)$")
_QUEUE_START_PATTERN = re.compile(r"starting TSU generation: (Fuller_Complete_Works_Vol\d+)")
_QUEUE_COMPLETE_PATTERN = re.compile(r"(Fuller_Complete_Works_Vol\d+) COMPLETE \(partial=False\)")
_QUEUE_FAILED_PATTERN = re.compile(r"(Fuller_Complete_Works_Vol\d+) FAILED")


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
    ) -> None:
        self._tsu_root = tsu_root
        self._queue_log_path = queue_log_path
        self._stop_marker_path = stop_marker_path
        self._history_window = history_window_seconds
        self._ps_reader = ps_reader
        self._ollama_checker = ollama_checker

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

            report = None
            if active:
                report = read_json_safe(self._tsu_root / active / "tsu_report.json")

            now = time.time()
            with self._lock:
                self._state.active = active
                self._state.process_alive = active is not None
                self._state.ollama_online = ollama_online
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
