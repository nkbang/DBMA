"""Heartbeat monitoring and stale-worker detection.

Workers must send heartbeats at regular intervals. Workers that fail to
send heartbeats within the timeout window are marked as stale.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any


class WorkerHeartbeat:
    """Tracks heartbeat state for a single worker."""

    def __init__(self, worker_id: str, heartbeat_interval_s: float = 60.0):
        self.worker_id = worker_id
        self.heartbeat_interval_s = heartbeat_interval_s
        self.last_heartbeat_ts: float | None = None
        self.last_heartbeat_str: str = ""
        self.status = "UNKNOWN"
        self.record_heartbeat()

    def record_heartbeat(self) -> None:
        now = time.monotonic()
        self.last_heartbeat_ts = now
        self.last_heartbeat_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        self.status = "ALIVE"

    def is_stale(self) -> bool:
        if self.last_heartbeat_ts is None:
            return True
        elapsed = time.monotonic() - self.last_heartbeat_ts
        return elapsed > self.heartbeat_interval_s * 2

    @property
    def heartbeat_age_s(self) -> float | None:
        if self.last_heartbeat_ts is None:
            return None
        return time.monotonic() - self.last_heartbeat_ts


class HeartbeatMonitor:
    """Monitors heartbeats from all workers and detects stale ones."""

    def __init__(self, default_interval_s: float = 60.0):
        self.default_interval_s = default_interval_s
        self._workers: dict[str, WorkerHeartbeat] = {}
        self._stale_log: list[dict[str, Any]] = []

    def register_worker(self, worker_id: str, interval_s: float | None = None) -> None:
        """Register a new worker."""
        self._workers[worker_id] = WorkerHeartbeat(
            worker_id, interval_s or self.default_interval_s
        )

    def record_heartbeat(self, worker_id: str) -> tuple[bool, str]:
        """Record a heartbeat from a worker. Returns (success, message)."""
        if worker_id not in self._workers:
            return (False, f"worker {worker_id} not registered")
        self._workers[worker_id].record_heartbeat()
        return (True, f"heartbeat recorded for {worker_id}")

    def detect_stale_workers(self) -> list[str]:
        """Detect all stale workers. Returns list of stale worker_ids."""
        stale = []
        for wid, wh in self._workers.items():
            if wh.is_stale():
                stale.append(wid)
                self._stale_log.append({
                    "worker_id": wid,
                    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                    "heartbeat_age_s": wh.heartbeat_age_s,
                })
        return stale

    def get_worker_status(self, worker_id: str) -> dict[str, Any] | None:
        """Get the current status of a worker."""
        wh = self._workers.get(worker_id)
        if wh is None:
            return None
        return {
            "worker_id": wh.worker_id,
            "status": wh.status,
            "last_heartbeat": wh.last_heartbeat_str,
            "heartbeat_age_s": wh.heartbeat_age_s,
            "is_stale": wh.is_stale(),
        }

    @property
    def all_workers(self) -> dict[str, dict[str, Any]]:
        return {wid: self.get_worker_status(wid) for wid in self._workers}

    @property
    def stale_log(self) -> list[dict[str, Any]]:
        return list(self._stale_log)
