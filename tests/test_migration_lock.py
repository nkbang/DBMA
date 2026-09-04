"""Tests for scripts/migration_lock.py (NAE-METADATA-MIGRATION-IMPLEMENTATION-001)."""

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.migration_lock import MigrationLock


class TestAcquireRelease:
    def test_acquire_then_release(self, tmp_path):
        lock = MigrationLock(tmp_path / "lock.json")
        assert lock.acquire(owner="unit_a") is True
        assert lock.is_locked() is True
        assert lock.release(owner="unit_a") is True
        assert lock.is_locked() is False

    def test_second_owner_cannot_acquire_while_held(self, tmp_path):
        lock_path = tmp_path / "lock.json"
        lock_a = MigrationLock(lock_path)
        lock_b = MigrationLock(lock_path)
        assert lock_a.acquire(owner="unit_a") is True
        assert lock_b.acquire(owner="unit_b") is False

    def test_release_by_wrong_owner_fails(self, tmp_path):
        lock = MigrationLock(tmp_path / "lock.json")
        lock.acquire(owner="unit_a")
        assert lock.release(owner="unit_b") is False
        assert lock.is_locked() is True

    def test_same_owner_can_reacquire(self, tmp_path):
        lock = MigrationLock(tmp_path / "lock.json")
        assert lock.acquire(owner="unit_a") is True
        assert lock.acquire(owner="unit_a") is True


class TestStaleLockRecovery:
    def test_stale_lock_is_recoverable(self, tmp_path):
        lock_path = tmp_path / "lock.json"
        lock = MigrationLock(lock_path, stale_after_seconds=0.05)
        lock.acquire(owner="unit_a")
        time.sleep(0.1)
        assert lock.is_stale() is True

        other = MigrationLock(lock_path, stale_after_seconds=0.05)
        assert other.acquire(owner="unit_b") is True

    def test_non_stale_lock_blocks_other_owner(self, tmp_path):
        lock_path = tmp_path / "lock.json"
        lock = MigrationLock(lock_path, stale_after_seconds=3600.0)
        lock.acquire(owner="unit_a")
        other = MigrationLock(lock_path, stale_after_seconds=3600.0)
        assert other.acquire(owner="unit_b") is False

    def test_force_acquire_overrides_non_stale_lock(self, tmp_path):
        lock_path = tmp_path / "lock.json"
        lock = MigrationLock(lock_path)
        lock.acquire(owner="unit_a")
        other = MigrationLock(lock_path)
        assert other.acquire(owner="unit_b", force=True) is True
