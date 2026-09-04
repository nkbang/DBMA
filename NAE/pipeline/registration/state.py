"""Registration state machine + exception queue (ADR-021 SS10, SS11).

Physically separate from ADR-020's NAE/pipeline/ingest/state.py (different
file, different enum, different lifecycle — that module is untouched by
this ADR) and from NAE/review/human/exception_queue.json (Production
human-review queue — upstream failures here must never land in it).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from . import config


class RegistrationState(str, Enum):
    DISCOVERED = "DISCOVERED"
    REGISTERED = "REGISTERED"
    RAW_PRESERVED = "RAW_PRESERVED"
    VALIDATED = "VALIDATED"
    EXTRACTED = "EXTRACTED"
    QUALITY_PASSED = "QUALITY_PASSED"

    REGISTRATION_FAILED = "REGISTRATION_FAILED"
    RAW_CHECKSUM_MISMATCH = "RAW_CHECKSUM_MISMATCH"
    EXTRACTION_FAILED = "EXTRACTION_FAILED"
    QUALITY_GATE_FAILED = "QUALITY_GATE_FAILED"


FAILURE_STATES = {
    RegistrationState.REGISTRATION_FAILED,
    RegistrationState.RAW_CHECKSUM_MISMATCH,
    RegistrationState.EXTRACTION_FAILED,
    RegistrationState.QUALITY_GATE_FAILED,
}


class RegistrationStateStore:
    """source_id -> {state, updated_at} map. One source's failure never
    blocks another source's registration (independent per-record state,
    same principle as ADR-020's IncrementalStateStore)."""

    def __init__(self, path: Path = config.DEFAULT_REGISTRATION_STATE_PATH):
        self.path = path
        self._data: dict[str, dict[str, Any]] = {}
        if path.exists():
            self._data = json.loads(path.read_text(encoding="utf-8"))

    def get_state(self, source_id: str) -> RegistrationState | None:
        entry = self._data.get(source_id)
        return RegistrationState(entry["state"]) if entry else None

    def set_state(self, source_id: str, state: RegistrationState) -> None:
        entry = self._data.setdefault(source_id, {})
        entry["state"] = state.value
        entry["updated_at"] = datetime.now(timezone.utc).isoformat()

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8")

    def summary(self) -> dict[str, int]:
        from collections import Counter
        return dict(Counter(e["state"] for e in self._data.values()))


class ExceptionQueue:
    """Upstream-only exception record. Never writes to
    NAE/review/human/exception_queue.json — that queue belongs to the
    downstream/Production human-review process (ADR-020) and must not be
    mixed with pre-TSU registration failures."""

    def __init__(self, path: Path = config.DEFAULT_EXCEPTION_QUEUE_PATH):
        self.path = path
        self._entries: list[dict[str, Any]] = []
        if path.exists():
            self._entries = json.loads(path.read_text(encoding="utf-8"))

    def record(self, source_id: str, failure_state: RegistrationState, reason: str, *, raw_path: str | None = None, checksum: str | None = None) -> None:
        self._entries.append({
            "source_id": source_id,
            "failure_state": failure_state.value,
            "reason": reason,
            "raw_path": raw_path,
            "checksum_at_failure": checksum,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._entries, ensure_ascii=False, indent=2), encoding="utf-8")

    def entries(self) -> list[dict[str, Any]]:
        return list(self._entries)
