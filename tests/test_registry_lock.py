"""Regression test — core/identity_registry.py::registry_lock().

2026-08-23: core/processing.py::process_one_file() (foreground, per-file
during batch processing) and core/index_orchestrator.py::reconcile_pending()
(background daemon thread) each independently load_identity_registry() ->
mutate -> save_identity_registry() the same file with no coordination. A
batch run long enough for the background tick to fire mid-batch loses
whichever addition the background thread's stale snapshot didn't know
about when it saved — no exception, no log line (confirmed: 49 freshly-
chunked documents vanished from the registry this way in one real run).

This test reproduces the interleaving with two threads and asserts that
registry_lock() makes both writers' additions survive.
"""

import sys
import os
import threading
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.identity_registry import (
    load_identity_registry,
    save_identity_registry,
    registry_lock,
    _empty_registry,
)


def _write_one_entry(registry_path: str, doc_id: str, delay_before_save: float, use_lock: bool):
    """Mirrors the shape of both real call sites: load -> mutate -> (delay,
    simulating slow work between load and save) -> save."""
    def _do():
        registry = load_identity_registry(registry_path)
        registry["documents"][doc_id] = {"document_id": doc_id}
        time.sleep(delay_before_save)  # widen the interleaving window deterministically
        save_identity_registry(registry, registry_path)

    if use_lock:
        with registry_lock(registry_path):
            _do()
    else:
        _do()


class TestRegistryLockPreventsLostUpdate:
    def test_concurrent_writes_without_lock_can_lose_an_update(self, tmp_path):
        """Establishes the bug exists absent the lock — thread A's addition
        is lost because thread B loaded before A saved and then overwrote
        with its own (A-less) snapshot."""
        registry_path = str(tmp_path / "identity_registry.json")
        save_identity_registry(_empty_registry(), registry_path)

        t_a = threading.Thread(target=_write_one_entry, args=(registry_path, "doc-a", 0.2, False))
        t_b = threading.Thread(target=_write_one_entry, args=(registry_path, "doc-b", 0.0, False))
        t_a.start()
        time.sleep(0.05)  # ensure A has already loaded (and is mid-delay) before B loads+saves
        t_b.start()
        t_a.join()
        t_b.join()

        final = load_identity_registry(registry_path)
        # doc-a's addition is expected to be clobbered by B's stale save —
        # if this assertion ever starts failing, the underlying race may
        # have changed shape; re-verify before assuming it's fixed.
        assert "doc-a" not in final["documents"] or "doc-b" not in final["documents"]

    def test_concurrent_writes_with_lock_preserve_both_updates(self, tmp_path):
        registry_path = str(tmp_path / "identity_registry.json")
        save_identity_registry(_empty_registry(), registry_path)

        t_a = threading.Thread(target=_write_one_entry, args=(registry_path, "doc-a", 0.2, True))
        t_b = threading.Thread(target=_write_one_entry, args=(registry_path, "doc-b", 0.0, True))
        t_a.start()
        time.sleep(0.05)
        t_b.start()
        t_a.join()
        t_b.join()

        final = load_identity_registry(registry_path)
        assert "doc-a" in final["documents"]
        assert "doc-b" in final["documents"]


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
