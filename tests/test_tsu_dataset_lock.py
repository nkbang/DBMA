"""Regression: core.tsu_builder.tsu_dataset_lock() serializes read-modify-write
of tsu_dataset.jsonl across threads and processes, and is reentrant within a
thread.

[2026-09-07 incident] tsu_dataset.jsonl had no lock — only registry_lock()
(documents.json). The Streamlit foreground (exclude_document_from_index) and
the 5s BackgroundIndexBuilder daemon (reconcile_pending -> reindex_document)
both rewrote the dataset non-atomically with no coordination, interleaving
into a NUL-holed file.
"""
from __future__ import annotations

import subprocess
import sys
import threading
import time
from pathlib import Path

from core.tsu_builder import tsu_dataset_lock


def test_reentrant_same_thread_no_deadlock(tmp_path):
    p = tmp_path / "ds.jsonl"
    with tsu_dataset_lock(p):
        with tsu_dataset_lock(p):
            with tsu_dataset_lock(p):
                pass  # would hang if the flock were re-taken instead of counted


def test_mutual_exclusion_across_threads(tmp_path):
    p = tmp_path / "ds.jsonl"
    order: list[str] = []

    def worker(tag: str) -> None:
        with tsu_dataset_lock(p):
            order.append(f"{tag}-in")
            time.sleep(0.15)
            order.append(f"{tag}-out")

    a = threading.Thread(target=worker, args=("A",))
    b = threading.Thread(target=worker, args=("B",))
    a.start()
    time.sleep(0.03)
    b.start()
    a.join()
    b.join()

    # whichever ran first, its in/out are not interleaved with the other's
    assert order in (
        ["A-in", "A-out", "B-in", "B-out"],
        ["B-in", "B-out", "A-in", "A-out"],
    ), order


def test_lock_uses_sibling_lock_file_not_the_dataset(tmp_path):
    p = tmp_path / "ds.jsonl"
    with tsu_dataset_lock(p):
        assert (tmp_path / "ds.jsonl.lock").exists()
        assert not p.exists()  # the dataset itself is untouched by the lock


def test_lock_released_on_exception(tmp_path):
    p = tmp_path / "ds.jsonl"
    try:
        with tsu_dataset_lock(p):
            raise RuntimeError("boom")
    except RuntimeError:
        pass
    # a fresh acquire must not hang
    done = threading.Event()

    def grab() -> None:
        with tsu_dataset_lock(p):
            done.set()

    t = threading.Thread(target=grab)
    t.start()
    t.join(timeout=2)
    assert done.is_set()


_CHILD = """
import sys, time
sys.path.insert(0, {root!r})
from core.tsu_builder import tsu_dataset_lock
with tsu_dataset_lock({path!r}):
    print("child-holding", flush=True)
    time.sleep(1.0)
"""


def test_mutual_exclusion_across_processes(tmp_path):
    p = tmp_path / "ds.jsonl"
    root = str(Path(__file__).resolve().parent.parent)
    child = subprocess.Popen(
        [sys.executable, "-c", _CHILD.format(root=root, path=str(p))],
        stdout=subprocess.PIPE, text=True,
    )
    try:
        assert child.stdout.readline().strip() == "child-holding"
        t0 = time.monotonic()
        with tsu_dataset_lock(p):
            waited = time.monotonic() - t0
        # parent had to wait for the child's ~1s hold to end
        assert waited > 0.5, waited
    finally:
        child.wait(timeout=5)
