"""NAE Live Dashboard — polling orchestration.

Ties together collector.py's raw reads, pipeline_stages.py's stage
judgment, bottleneck.py's threshold check, gpu_health.py's health verdict,
and events.py's transition log into one background-polled snapshot.
`poll()` does all the IO and computation on a timer from a background
thread; `snapshot()` only reads already-computed state under a lock and
never touches disk/network/ps itself, so request handlers never block on
IO.
"""
from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import bottleneck as bottleneck_mod
import collector
import events as events_mod
import gpu_health as gpu_health_mod
import pipeline_stages


def _safe(reader: Callable[[], object], default: object):
    """A slow/unavailable system-metrics reader (psutil hiccup, ioreg
    absent on non-Apple hardware, Ollama/n8n briefly unreachable) must
    not knock out the TSU progress read it's bundled with in the same
    poll cycle — each of these is independently best-effort."""
    try:
        return reader()
    except Exception:
        return default


@dataclass
class ThroughputSample:
    ts: float
    evaluated: int
    elapsed_seconds: float = 0.0


@dataclass
class SystemSample:
    ts: float
    gpu_pct: float | None
    vram_bytes: float | None
    ram_pct: float | None
    cpu_pct: float | None


@dataclass
class _PolledState:
    active: str | None = None
    process_alive: bool = False
    ollama_online: bool = False
    n8n_online: bool = False
    last_poll_ts: float | None = None
    last_poll_ok: bool = False

    memory: dict | None = None
    cpu: dict | None = None
    gpu: dict | None = None
    disk: dict | None = None
    disk_io_rate: dict | None = None
    network_io_rate: dict | None = None
    thermal_pressure: str = "unknown"
    llama_parallelism: list = field(default_factory=list)
    ollama_models: list = field(default_factory=list)

    queue: list = field(default_factory=list)
    queue_stopped: bool = False
    queue_stop_reason: str | None = None

    pipeline_stages: list = field(default_factory=list)
    bottleneck: dict | None = None
    gpu_health: dict | None = None


class MonitorState:
    def __init__(
        self,
        *,
        tsu_root: Path = collector.TSU_ROOT,
        queue_log_path: Path = collector.QUEUE_LOG_PATH,
        stop_marker_path: Path = collector.STOP_MARKER_PATH,
        history_window_seconds: float = 3600.0,
        ps_reader: Callable[[], str] = collector.read_ps_aux,
        ollama_checker: Callable[[], bool] = collector.check_ollama_online,
        n8n_checker: Callable[[], bool] = collector.check_n8n_online,
        memory_reader: Callable[[], dict] = collector.read_system_memory,
        cpu_reader: Callable[[], dict] = collector.read_cpu_stats,
        gpu_reader: Callable[[], str] = collector.read_gpu_stats_raw,
        disk_reader: Callable[[], dict] = collector.read_disk_usage,
        disk_io_reader: Callable[[], dict | None] = collector.read_disk_io_raw,
        net_io_reader: Callable[[], dict | None] = collector.read_net_io_raw,
        thermal_reader: Callable[[], str] = collector.read_thermal_pressure_raw,
        ollama_models_reader: Callable[[], list] = collector.read_ollama_models,
        registration_state_reader: Callable[[], dict] = collector.read_registration_state,
    ) -> None:
        self._tsu_root = tsu_root
        self._queue_log_path = queue_log_path
        self._stop_marker_path = stop_marker_path
        self._history_window = history_window_seconds
        self._ps_reader = ps_reader
        self._ollama_checker = ollama_checker
        self._n8n_checker = n8n_checker
        self._memory_reader = memory_reader
        self._cpu_reader = cpu_reader
        self._gpu_reader = gpu_reader
        self._disk_reader = disk_reader
        self._disk_io_reader = disk_io_reader
        self._net_io_reader = net_io_reader
        self._thermal_reader = thermal_reader
        self._ollama_models_reader = ollama_models_reader
        self._registration_state_reader = registration_state_reader

        self._lock = threading.Lock()
        self._state = _PolledState()
        self._reports: dict[str, dict] = {}
        self._throughput_history: dict[str, deque[ThroughputSample]] = {}
        self._system_history: deque[SystemSample] = deque()
        self._event_log = events_mod.EventLog()
        self._prev_event_facts: dict | None = None
        self._prev_disk_io: dict | None = None
        self._prev_net_io: dict | None = None

    def poll(self) -> None:
        """One read+compute cycle. Never raises — a failed poll just
        leaves the previous snapshot in place so the dashboard degrades
        gracefully instead of going blank."""
        try:
            ps_text = self._ps_reader()
            active = collector.parse_active_identifier(ps_text)
            ollama_online = self._ollama_checker()
            n8n_online = _safe(self._n8n_checker, False)
            memory = _safe(self._memory_reader, None)
            cpu = _safe(self._cpu_reader, None)
            gpu = _safe(lambda: collector.parse_gpu_stats(self._gpu_reader()), None)
            disk = _safe(self._disk_reader, None)
            disk_io_raw = _safe(self._disk_io_reader, None)
            net_io_raw = _safe(self._net_io_reader, None)
            thermal = _safe(lambda: collector.parse_thermal_pressure(self._thermal_reader()), "unknown")
            llama_parallelism = _safe(lambda: collector.parse_llama_server_parallelism(ps_text), [])
            ollama_models = _safe(self._ollama_models_reader, [])
            registration_state = _safe(self._registration_state_reader, {})

            report = None
            if active:
                report = collector.read_json_safe(self._tsu_root / active / "tsu_report.json")

            now = time.time()

            disk_io_rate = self._rate_since_last(self._prev_disk_io, disk_io_raw, now,
                                                   {"read_bytes": "read_bytes_per_sec", "write_bytes": "write_bytes_per_sec"})
            if disk_io_raw is not None:
                self._prev_disk_io = {"ts": now, **disk_io_raw}

            net_io_rate = self._rate_since_last(self._prev_net_io, net_io_raw, now,
                                                  {"bytes_sent": "sent_bytes_per_sec", "bytes_recv": "recv_bytes_per_sec"})
            if net_io_raw is not None:
                self._prev_net_io = {"ts": now, **net_io_raw}

            queue, queue_stopped, queue_stop_reason = self._compute_queue_snapshot(active, report)

            stages: list[dict] = []
            if active:
                tsu_records = collector.read_json_safe(self._tsu_root / active / "tsu.json")
                index_report = collector.read_index_report(self._tsu_root, active)
                extraction_status = next((q["status"] for q in queue if q["identifier"] == active), "QUEUED")
                stages = pipeline_stages.compute_pipeline_stages(
                    identifier=active,
                    registration_state=registration_state,
                    tsu_records=tsu_records if isinstance(tsu_records, list) else None,
                    extraction_status=extraction_status,
                    index_report=index_report,
                )

            bottleneck_verdict = bottleneck_mod.compute_bottleneck(
                gpu_pct=gpu.get("device_utilization_pct") if gpu else None,
                cpu_pct=cpu.get("percent") if cpu else None,
                ram_pct=memory.get("percent") if memory else None,
                ollama_active=bool(ollama_models),
            )
            gpu_health_verdict = gpu_health_mod.compute_gpu_health(gpu_stats=gpu, thermal_pressure=thermal)

            with self._lock:
                self._state.active = active
                self._state.process_alive = active is not None
                self._state.ollama_online = ollama_online
                self._state.n8n_online = n8n_online
                self._state.memory = memory
                self._state.cpu = cpu
                self._state.gpu = gpu
                self._state.disk = disk
                self._state.disk_io_rate = disk_io_rate
                self._state.network_io_rate = net_io_rate
                self._state.thermal_pressure = thermal
                self._state.llama_parallelism = llama_parallelism
                self._state.ollama_models = ollama_models
                self._state.queue = queue
                self._state.queue_stopped = queue_stopped
                self._state.queue_stop_reason = queue_stop_reason
                self._state.pipeline_stages = stages
                self._state.bottleneck = bottleneck_verdict
                self._state.gpu_health = gpu_health_verdict
                self._state.last_poll_ts = now
                self._state.last_poll_ok = True

                if active and report is not None:
                    self._reports[active] = report
                    hist = self._throughput_history.setdefault(active, deque())
                    hist.append(ThroughputSample(
                        ts=now,
                        evaluated=report.get("candidates_evaluated", 0),
                        elapsed_seconds=report.get("elapsed_seconds", 0.0),
                    ))
                    self._prune_by_age(hist, now)

                self._system_history.append(SystemSample(
                    ts=now,
                    gpu_pct=gpu.get("device_utilization_pct") if gpu else None,
                    vram_bytes=gpu.get("in_use_memory_bytes") if gpu else None,
                    ram_pct=memory.get("percent") if memory else None,
                    cpu_pct=cpu.get("percent") if cpu else None,
                ))
                self._prune_by_age(self._system_history, now)

                facts = {
                    "active": active,
                    "processed": report.get("candidates_evaluated", 0) if report else 0,
                    "total": report.get("candidates_total", 0) if report else 0,
                    "percentage": round(100 * report.get("candidates_evaluated", 0) / report["candidates_total"], 2)
                                  if report and report.get("candidates_total") else 0.0,
                    "errors": report.get("llm_errors", 0) if report else 0,
                    "process_alive": active is not None,
                    "ollama_online": ollama_online,
                    "n8n_online": n8n_online,
                    "queue": {q["identifier"]: q["status"] for q in queue},
                    "queue_stopped": queue_stopped,
                    "queue_stop_reason": queue_stop_reason,
                }
                for level, message in events_mod.diff_events(self._prev_event_facts, facts):
                    self._event_log.add(level, message, ts=now)
                self._prev_event_facts = facts
        except Exception:
            with self._lock:
                self._state.last_poll_ts = time.time()
                self._state.last_poll_ok = False

    def _prune_by_age(self, buf: deque, now: float) -> None:
        cutoff = now - self._history_window
        while buf and buf[0].ts < cutoff:
            buf.popleft()

    @staticmethod
    def _rate_since_last(prev: dict | None, cur: dict | None, now: float, fields: dict[str, str]) -> dict | None:
        if cur is None or prev is None:
            return None
        dt = now - prev["ts"]
        if dt <= 0:
            return None
        return {out_key: max(0.0, (cur[in_key] - prev[in_key]) / dt) for in_key, out_key in fields.items()}

    def _compute_queue_snapshot(self, active: str | None, active_report: dict | None) -> tuple[list[dict], bool, str | None]:
        log_text = ""
        try:
            log_text = self._queue_log_path.read_text(encoding="utf-8")
        except OSError:
            pass
        queue_statuses = collector.parse_queue_log(log_text)

        stopped = self._stop_marker_path.exists()
        stop_reason = None
        if stopped:
            try:
                stop_reason = self._stop_marker_path.read_text(encoding="utf-8").strip().splitlines()[0]
            except (OSError, IndexError):
                stop_reason = "STOP.md present"

        entries = []
        for vol in collector.VOLUME_QUEUE:
            if vol == active:
                report = active_report or {}
                total = report.get("candidates_total") or 0
                evaluated = report.get("candidates_evaluated") or 0
                pct = round(100 * evaluated / total, 1) if total else 0.0
                entries.append({"identifier": vol, "status": "RUNNING", "progress_pct": pct})
                continue

            on_disk = collector.read_json_safe(self._tsu_root / vol / "tsu_report.json")
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
            n8n_online = self._state.n8n_online
            last_poll_ts = self._state.last_poll_ts
            last_poll_ok = self._state.last_poll_ok
            memory = dict(self._state.memory) if self._state.memory else None
            cpu = dict(self._state.cpu) if self._state.cpu else None
            gpu = dict(self._state.gpu) if self._state.gpu else None
            disk = dict(self._state.disk) if self._state.disk else None
            disk_io_rate = dict(self._state.disk_io_rate) if self._state.disk_io_rate else None
            network_io_rate = dict(self._state.network_io_rate) if self._state.network_io_rate else None
            thermal_pressure = self._state.thermal_pressure
            llama_parallelism = list(self._state.llama_parallelism)
            ollama_models = list(self._state.ollama_models)
            queue = list(self._state.queue)
            queue_stopped = self._state.queue_stopped
            stop_reason = self._state.queue_stop_reason
            stages = list(self._state.pipeline_stages)
            bottleneck_verdict = dict(self._state.bottleneck) if self._state.bottleneck else None
            gpu_health_verdict = dict(self._state.gpu_health) if self._state.gpu_health else None
            report = dict(self._reports.get(active, {})) if active else None
            throughput_hist = list(self._throughput_history.get(active, [])) if active else []
            system_hist = list(self._system_history)
            recent_events = self._event_log.recent()

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

        throughput_sparkline = []
        latency_sparkline = []
        for prev, cur in zip(throughput_hist, throughput_hist[1:]):
            dt = cur.ts - prev.ts
            d_ev = cur.evaluated - prev.evaluated
            rate_per_hour = (d_ev / dt * 3600) if dt > 0 else 0.0
            throughput_sparkline.append({"t": cur.ts, "rate_per_hour": round(rate_per_hour, 1)})

            d_elapsed = cur.elapsed_seconds - prev.elapsed_seconds
            if d_ev > 0:
                latency_sparkline.append({"t": cur.ts, "sec_per_item": round(d_elapsed / d_ev, 2)})

        gpu_history = [{"t": s.ts, "value": s.gpu_pct} for s in system_hist if s.gpu_pct is not None]
        vram_history = [{"t": s.ts, "value": s.vram_bytes} for s in system_hist if s.vram_bytes is not None]
        ram_history = [{"t": s.ts, "value": s.ram_pct} for s in system_hist if s.ram_pct is not None]
        cpu_history = [{"t": s.ts, "value": s.cpu_pct} for s in system_hist if s.cpu_pct is not None]

        return {
            "current_source": {
                "identifier": active,
                "title": collector.volume_title(active) if active else None,
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
            "n8n_online": n8n_online,
            "system": {
                "memory": memory,
                "cpu": cpu,
                "gpu": gpu,
                "disk": disk,
                "disk_io_rate": disk_io_rate,
                "network_io_rate": network_io_rate,
                "thermal_pressure": thermal_pressure,
            },
            "llama_parallelism": llama_parallelism,
            "ollama_models": ollama_models,
            "pipeline_stages": stages,
            "bottleneck": bottleneck_verdict,
            "gpu_health": gpu_health_verdict,
            "gpu_extended": {
                # Always null here — not obtainable without `powermetrics`
                # (sudo) or a custom native IOReport/SMC client, neither of
                # which this dashboard uses. See gpu_health.py's docstring.
                "temperature_c": None,
                "power_watts": None,
                "power_limit_watts": None,
                "clock_mhz": None,
                "performance_state": None,
            },
            "queue": queue,
            "queue_stopped": queue_stopped,
            "queue_stop_reason": stop_reason,
            "throughput_history": throughput_sparkline,
            "latency_history": latency_sparkline,
            "gpu_history": gpu_history,
            "vram_history": vram_history,
            "ram_history": ram_history,
            "cpu_history": cpu_history,
            "events": recent_events,
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
