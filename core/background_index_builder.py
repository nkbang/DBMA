"""core/background_index_builder.py — Background Index Builder (DBMA-SEARCH-INFRA-001 HQ 제안 ⑧).

HQ: "문서 추가 시 사용자는 기다리지 않는다. 등록 → Queue → Background →
Index → Ready로 동작한다."

The "Queue" already exists in this codebase: `core/document_context.py`'s
`pipeline_state` field has a `PROCESSED` state meaning "extracted, not yet
indexed", and `core/index_orchestrator.py::reconcile_pending()` is already a
pull-based, idempotent reconciler over exactly that queue (finds every
`PROCESSED` document, indexes it, advances it to `INDEXED`). What was
missing is running that on a background thread instead of blocking whatever
call site currently calls it synchronously — this module is that thread,
not a new pipeline.

`reconcile_pending()`/`core/index_orchestrator.py` are called, not
reimplemented or modified.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Optional

from core.config import DEFAULT_OUTPUT_DIR
from core.index_orchestrator import reconcile_pending


class BackgroundIndexBuilder:
    """A daemon thread that calls `reconcile_pending()` periodically, plus
    an immediate wake-up (`trigger_now()`) for "a document just finished
    processing, index it soon" without the caller waiting for the reconcile
    itself. One instance is meant to live for the lifetime of the process
    (see `ui/state/background_builder.py` for the Streamlit-side singleton).
    """

    def __init__(self, output_dir: str = DEFAULT_OUTPUT_DIR, interval_seconds: float = 5.0) -> None:
        self.output_dir = output_dir
        self.interval_seconds = interval_seconds
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._trigger_event = threading.Event()
        self._lock = threading.Lock()
        self._last_result: Optional[dict[str, Any]] = None
        self._last_error: Optional[str] = None
        self._last_run_at: Optional[float] = None
        self._is_running_job = False

    def start(self) -> None:
        """Start the worker thread. No-op if already running."""
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="BackgroundIndexBuilder")
        self._thread.start()

    def stop(self, timeout: float = 2.0) -> None:
        self._stop_event.set()
        self._trigger_event.set()  # wake it if it's waiting, so it can see the stop
        if self._thread is not None:
            self._thread.join(timeout=timeout)

    def trigger_now(self) -> None:
        """Wake the worker immediately instead of waiting for the next
        interval tick. Returns immediately — this is the "사용자는 기다리지
        않는다" call site; the actual indexing runs on the background
        thread."""
        self._trigger_event.set()

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            self._trigger_event.wait(timeout=self.interval_seconds)
            if self._stop_event.is_set():
                break
            self._trigger_event.clear()
            self._run_once()

    def _run_once(self) -> None:
        with self._lock:
            self._is_running_job = True
        try:
            result = reconcile_pending(self.output_dir)
            with self._lock:
                self._last_result = result
                self._last_error = None
        except Exception as e:
            # reconcile_pending() itself never raises (per-document failures
            # go into its "failed" list) — this catches anything else
            # unexpected (e.g. a registry file read error) so one bad tick
            # never kills the background thread.
            with self._lock:
                self._last_error = str(e)
        finally:
            with self._lock:
                self._is_running_job = False
                self._last_run_at = time.time()

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "is_alive": self._thread is not None and self._thread.is_alive(),
                "is_running_job": self._is_running_job,
                "last_run_at": self._last_run_at,
                "last_result": self._last_result,
                "last_error": self._last_error,
            }
