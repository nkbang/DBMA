"""NAE Live Dashboard — event/alert timeline.

`EventLog` is a bounded, in-memory log of *meaningful state transitions*
observed between successive polls (checkpoint saved, queue status
changed, error count increased, a health check flipped). It does not log
every poll tick — only changes — so the timeline stays legible instead of
flooding with a new row every 5 seconds. Purely an observation log: it
never triggers or blocks anything.
"""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass


@dataclass
class Event:
    ts: float
    level: str  # "info" | "warn" | "error"
    message: str


class EventLog:
    def __init__(self, max_events: int = 200, max_age_seconds: float = 4 * 3600.0) -> None:
        self._events: deque[Event] = deque()
        self._max_events = max_events
        self._max_age_seconds = max_age_seconds

    def add(self, level: str, message: str, ts: float | None = None) -> None:
        resolved_ts = ts if ts is not None else time.time()
        self._events.append(Event(ts=resolved_ts, level=level, message=message))
        self._prune(now=resolved_ts)

    def _prune(self, now: float) -> None:
        # Pruning relative to the just-added event's own timestamp (rather
        # than a fresh time.time() call) keeps this deterministic/testable
        # without a clock double, and is equivalent in practice since add()
        # is always called with a near-real-time ts.
        cutoff = now - self._max_age_seconds
        while self._events and self._events[0].ts < cutoff:
            self._events.popleft()
        while len(self._events) > self._max_events:
            self._events.popleft()

    def recent(self, limit: int = 50) -> list[dict]:
        items = list(self._events)[-limit:]
        items.reverse()  # newest first
        return [{"ts": e.ts, "level": e.level, "message": e.message} for e in items]


def diff_events(prev: dict | None, cur: dict) -> list[tuple[str, str]]:
    """Pure function comparing two consecutive *fact* snapshots — a small
    dict of just the fields worth watching (see monitor_state.py's
    `_event_facts`), not the full API response — and returns
    [(level, message), ...] for whatever meaningfully changed.
    `prev is None` (first poll) never emits events, since there is
    nothing to compare against yet."""
    if prev is None:
        return []

    events: list[tuple[str, str]] = []

    if cur.get("active") and cur.get("processed", 0) != prev.get("processed", 0):
        events.append((
            "info",
            f"checkpoint saved — {cur['processed']}/{cur.get('total', 0)} processed "
            f"({cur.get('percentage', 0.0):.1f}%)",
        ))

    if cur.get("errors", 0) > prev.get("errors", 0):
        events.append(("warn", f"llm_errors increased: {prev.get('errors', 0)} -> {cur['errors']}"))

    if prev.get("process_alive") and not cur.get("process_alive"):
        events.append(("error", "TSU process stopped"))
    elif not prev.get("process_alive") and cur.get("process_alive"):
        events.append(("info", "TSU process resumed"))

    if prev.get("ollama_online") and not cur.get("ollama_online"):
        events.append(("error", "Ollama offline"))
    elif not prev.get("ollama_online") and cur.get("ollama_online"):
        events.append(("info", "Ollama back online"))

    if prev.get("n8n_online") and not cur.get("n8n_online"):
        events.append(("warn", "n8n offline"))
    elif not prev.get("n8n_online") and cur.get("n8n_online"):
        events.append(("info", "n8n back online"))

    prev_queue: dict = prev.get("queue") or {}
    cur_queue: dict = cur.get("queue") or {}
    for vol, status in cur_queue.items():
        prev_status = prev_queue.get(vol)
        if prev_status is not None and prev_status != status:
            level = "error" if status == "FAILED" else "info"
            events.append((level, f"{vol}: {prev_status} -> {status}"))

    if prev.get("queue_stopped") is False and cur.get("queue_stopped") is True:
        events.append(("error", f"queue stopped — {cur.get('queue_stop_reason') or 'see STOP.md'}"))

    return events
