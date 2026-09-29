"""tests/test_search_cache_thread_safety.py -- Verify search_cache thread-safety fix.

Regression test for RPV-06b: sqlite3.connect() without check_same_thread
raises sqlite3.ProgrammingError when accessed from a different thread than
the one that created the connection.

Fix: added check_same_thread=False to sqlite3.connect() in _L2SqliteCache.__init__.

This test intentionally exercises concurrent get/set from multiple threads
to confirm the fix holds under load.
"""

import json
import os
import sys
import tempfile
import threading
import time
import traceback
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.search_cache import SearchResultCache, _L2SqliteCache


class ThreadResult:
    """Capture whether a thread succeeded or raised an exception."""

    def __init__(self) -> None:
        self.success = True
        self.exception = None

    def record_failure(self, exc):
        self.success = False
        self.exception = exc


def test_check_same_thread_flag_present():
    """Verify the source code contains check_same_thread=False."""
    src = (PROJECT_ROOT / "core" / "search_cache.py").read_text(encoding="utf-8")
    assert "check_same_thread=False" in src, (
        "sqlite3.connect() must include check_same_thread=False"
    )


def test_concurrent_get_set_basic():
    """Run concurrent get/set operations from multiple threads."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_cache.db")
        cache = SearchResultCache(db_path)

        num_threads = 8
        ops_per_thread = 50
        results = [ThreadResult() for _ in range(num_threads)]
        barrier = threading.Barrier(num_threads)

        def worker(thread_idx, result):
            try:
                barrier.wait(timeout=10)
                for i in range(ops_per_thread):
                    key = f"thread-{thread_idx}-op-{i}"
                    value = {"thread": thread_idx, "op": i, "ts": time.time()}
                    cache.set(key, value, ttl_seconds=300.0)
                    retrieved = cache.get(key)
                    assert retrieved is not None, f"get() returned None for {key}"
                    assert retrieved["thread"] == thread_idx
                    assert retrieved["op"] == i
            except Exception as exc:
                result.record_failure(exc)

        threads = [
            threading.Thread(target=worker, args=(i, results[i]))
            for i in range(num_threads)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=60)

        failures = [r for r in results if not r.success]
        cache.close()
        assert len(failures) == 0, (
            f"{len(failures)} thread(s) failed:\n"
            + "\n".join(
                f"Thread {i}: {type(r.exception).__name__}: {r.exception}\n"
                f"  {traceback.format_exc()}"
                for i, r in enumerate(failures)
            )
        )


def test_concurrent_l2_only():
    """Directly stress _L2SqliteCache from multiple threads (bypass L1)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_l2.db")
        l2 = _L2SqliteCache(db_path)

        num_threads = 12
        ops_per_thread = 100
        results = [ThreadResult() for _ in range(num_threads)]
        barrier = threading.Barrier(num_threads)

        def worker(thread_idx, result):
            try:
                barrier.wait(timeout=10)
                for i in range(ops_per_thread):
                    key = f"l2-t{thread_idx}-o{i}"
                    value_json = json.dumps(
                        {"t": thread_idx, "o": i}, ensure_ascii=False
                    )
                    l2.set(key, value_json, ttl_seconds=600.0)
                    retrieved = l2.get(key)
                    assert retrieved is not None
            except Exception as exc:
                result.record_failure(exc)

        threads = [
            threading.Thread(target=worker, args=(i, results[i]))
            for i in range(num_threads)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=60)

        failures = [r for r in results if not r.success]
        l2.close()
        assert len(failures) == 0, (
            f"{len(failures)} thread(s) failed:\n"
            + "\n".join(
                f"Thread {i}: {type(r.exception).__name__}: {r.exception}"
                for i, r in enumerate(failures)
            )
        )


def test_concurrent_mixed_operations():
    """Stress with mixed get/set/clear/purge_expired from multiple threads."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_mixed.db")
        cache = SearchResultCache(db_path)

        num_threads = 6
        ops_per_thread = 80
        results = [ThreadResult() for _ in range(num_threads)]
        barrier = threading.Barrier(num_threads)

        def worker(thread_idx, result):
            try:
                barrier.wait(timeout=10)
                for i in range(ops_per_thread):
                    key = f"mixed-t{thread_idx}-o{i}"
                    value = {"t": thread_idx, "o": i}
                    cache.set(key, value, ttl_seconds=60.0)
                    if i % 10 == 9:
                        cache.l2.purge_expired()
                    if i % 20 == 19 and thread_idx == 0:
                        cache.clear()
                    cache.get(key)
            except Exception as exc:
                result.record_failure(exc)

        threads = [
            threading.Thread(target=worker, args=(i, results[i]))
            for i in range(num_threads)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=60)

        failures = [r for r in results if not r.success]
        cache.close()
        assert len(failures) == 0, (
            f"{len(failures)} thread(s) failed:\n"
            + "\n".join(
                f"Thread {i}: {type(r.exception).__name__}: {r.exception}"
                for i, r in enumerate(failures)
            )
        )


if __name__ == "__main__":
    test_check_same_thread_flag_present()
    print("PASS: check_same_thread flag present")

    test_concurrent_get_set_basic()
    print("PASS: concurrent get/set basic (8 threads x 50 ops)")

    test_concurrent_l2_only()
    print("PASS: concurrent L2 only (12 threads x 100 ops)")

    test_concurrent_mixed_operations()
    print("PASS: concurrent mixed operations (6 threads x 80 ops)")

    print("\nAll thread-safety tests passed.")
