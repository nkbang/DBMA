"""Cross-platform inter-process / inter-thread advisory file lock.

Why this module exists
----------------------
core/identity_registry.py (registry_lock) and core/tsu_builder.py (tsu_dataset_lock) used
``fcntl.flock`` directly. ``fcntl`` is POSIX-only: on Windows ``import fcntl`` fails at import
time, so ``import ui.app`` failed and the app could not start (found 2026-10-12 while scoping
Windows support). Both call sites now go through ``file_lock()`` instead.

Implementation
--------------
A thin wrapper over the third-party ``filelock`` package (already in the dependency closure via
torch / huggingface_hub; now listed explicitly in requirements.txt). On POSIX ``filelock`` uses
``fcntl.flock`` — the same mechanism as before — and on Windows ``msvcrt.locking``. Keeping the
library behind this one function makes it cheap to swap later.

Semantics (unchanged from the previous fcntl code)
--------------------------------------------------
* The lock lives on a sibling ``<name>.lock`` file passed in by the caller, never on the data file
  itself, so the data file's atomic ``os.replace()`` stays undisturbed.
* Blocking acquire (no timeout) — callers wait until the lock is free. Pass ``timeout`` (seconds)
  to raise ``filelock.Timeout`` instead of waiting forever.
* Mutual exclusion holds across threads *and* processes: every call opens its own lock handle.
* NOT reentrant by design — nest through the caller's own bookkeeping (tsu_dataset_lock keeps a
  per-thread held counter, exactly as before).

Known differences by platform (see docs / PR notes)
---------------------------------------------------
* ``filelock`` polls (every 50 ms) instead of blocking in the kernel: ~10 ms extra wait under
  contention, ~0.1 ms per uncontended acquire.
* On Windows ``filelock`` deletes the lock file on release; on POSIX it stays on disk.
"""
from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator, Optional

from filelock import FileLock


@contextmanager
def file_lock(lock_path: "os.PathLike[str] | str", timeout: Optional[float] = None) -> Iterator[None]:
    """Hold an exclusive advisory lock on ``lock_path`` for the duration of the ``with`` block.

    Args:
        lock_path: path of the lock file (created if missing, together with its parent directory).
        timeout:   seconds to wait; ``None`` (default) waits indefinitely.
    """
    lock_path = os.fspath(lock_path)
    os.makedirs(os.path.dirname(lock_path) or ".", exist_ok=True)
    with FileLock(lock_path, timeout=-1 if timeout is None else timeout):
        yield
