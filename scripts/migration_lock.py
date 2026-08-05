"""scripts/migration_lock.py — Migration Engine 동시 실행 방지 Lock
(NAE-METADATA-MIGRATION-IMPLEMENTATION-001, 설계 §10).

파일 기반 Lock. 이 모듈은 어떤 Registry/Manifest/RAW 경로도 알지
못한다 — 호출자가 지정한 임의의 lock 파일 경로에 대해서만 동작한다.
"""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@dataclass
class LockInfo:
    owner: str
    pid: int
    acquired_at: float


class MigrationLock:
    """파일 기반 Migration Lock.

    stale lock(설계 §10 "Lock에는 timeout을 둔다") — acquired_at으로부터
    stale_after_seconds 이상 지난 lock은 자동으로 만료된 것으로 간주해
    회수 가능하다(§8 "중단" 상황에서 좀비 Lock이 영구히 남는 것을 방지).
    """

    def __init__(self, lock_path: Path, stale_after_seconds: float = 3600.0) -> None:
        self.lock_path = Path(lock_path)
        self.stale_after_seconds = stale_after_seconds

    def _read(self) -> LockInfo | None:
        if not self.lock_path.exists():
            return None
        try:
            data = json.loads(self.lock_path.read_text(encoding="utf-8"))
            return LockInfo(owner=data["owner"], pid=data["pid"], acquired_at=data["acquired_at"])
        except Exception:
            return None

    def is_stale(self) -> bool:
        info = self._read()
        if info is None:
            return False
        return (time.time() - info.acquired_at) > self.stale_after_seconds

    def is_locked(self) -> bool:
        return self.lock_path.exists() and not self.is_stale()

    def acquire(self, owner: str, force: bool = False) -> bool:
        """Lock 획득. 다른 소유자가 보유 중이고 stale이 아니면 실패(False).
        stale이거나 force=True면 회수 후 새로 획득(stale lock recovery)."""
        existing = self._read()
        if existing is not None and existing.owner != owner and not force and not self.is_stale():
            return False
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        info = {"owner": owner, "pid": os.getpid(), "acquired_at": time.time()}
        self.lock_path.write_text(json.dumps(info), encoding="utf-8")
        return True

    def release(self, owner: str | None = None) -> bool:
        """Lock 해제. owner가 주어지면 소유자가 일치할 때만 해제(오작동 방지)."""
        info = self._read()
        if info is None:
            return True
        if owner is not None and info.owner != owner:
            return False
        self.lock_path.unlink(missing_ok=True)
        return True

    def __enter__(self) -> "MigrationLock":
        return self

    def __exit__(self, *exc: object) -> None:
        pass
