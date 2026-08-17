"""TSU Extraction State Machine (Phase 3).

State transitions follow ADR-022 section 8 principles:
- No auto-retry: FAILED -> READY requires explicit human trigger
- No auto-promotion: EXTRACTED -> CONFIDENCE_CLASSIFIED is automatic
  (confidence classification is deterministic, not a review gate)
- Idempotent transitions: same state -> same state is a no-op

This state machine is PHYSICALLY SEPARATE from:
- Registration State Machine (ADR-021 section 10, NAE/pipeline/registration/state.py)
- Automation Task State Machine (ADR-022, .automation/tasks/schema.json)
- Human Review Disposition (ADR-020, NAE/review/human/)

Same naming convention as existing state machines in this repository.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


class TSUExtractionState(str, Enum):
    """TSU Extraction Queue state values."""

    READY = "READY"
    PROCESSING = "PROCESSING"
    EXTRACTED = "EXTRACTED"
    CONFIDENCE_CLASSIFIED = "CONFIDENCE_CLASSIFIED"
    FAILED = "FAILED"


TERMINAL_STATES = frozenset({TSUExtractionState.CONFIDENCE_CLASSIFIED})
FAILURE_STATES = frozenset({TSUExtractionState.FAILED})

VALID_TRANSITIONS: dict[TSUExtractionState, frozenset[TSUExtractionState]] = {
    TSUExtractionState.READY: frozenset({TSUExtractionState.PROCESSING}),
    TSUExtractionState.PROCESSING: frozenset({
        TSUExtractionState.EXTRACTED,
        TSUExtractionState.FAILED,
    }),
    TSUExtractionState.EXTRACTED: frozenset({TSUExtractionState.CONFIDENCE_CLASSIFIED}),
    TSUExtractionState.CONFIDENCE_CLASSIFIED: frozenset(),
    TSUExtractionState.FAILED: frozenset({TSUExtractionState.READY}),
}


def validate_transition(
    from_state: TSUExtractionState, to_state: TSUExtractionState,
) -> tuple[bool, str]:
    allowed = VALID_TRANSITIONS.get(from_state, frozenset())
    if to_state in allowed:
        return True, ""
    if from_state == to_state:
        return True, "idempotent (same state)"
    return False, f"{from_state.value} -> {to_state.value} is not allowed"


@dataclass
class StateEntry:
    candidate_id: str
    state: TSUExtractionState
    updated_at: str
    metadata: dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class TSUExtractionStateStore:
    """candidate_id -> StateEntry map. Independent per-record state."""

    def __init__(self, path: Path | None = None):
        if path is None:
            from . import config as worker_config
            path = worker_config.DEFAULT_STATE_PATH
        self.path = path
        self._data: dict[str, dict[str, Any]] = {}
        if path.exists():
            self._data = json.loads(path.read_text(encoding="utf-8"))

    def get_state(self, candidate_id: str) -> TSUExtractionState | None:
        entry = self._data.get(candidate_id)
        return TSUExtractionState(entry["state"]) if entry else None

    def get_entry(self, candidate_id: str) -> StateEntry | None:
        entry = self._data.get(candidate_id)
        if entry is None:
            return None
        return StateEntry(
            candidate_id=candidate_id,
            state=TSUExtractionState(entry["state"]),
            updated_at=entry["updated_at"],
            metadata=entry.get("metadata", {}),
        )

    def set_state(
        self,
        candidate_id: str,
        new_state: TSUExtractionState,
        *,
        from_state: TSUExtractionState | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> tuple[bool, str]:
        if from_state is not None:
            valid, reason = validate_transition(from_state, new_state)
            if not valid:
                return False, reason

        entry = self._data.setdefault(candidate_id, {})
        entry["state"] = new_state.value
        entry["updated_at"] = datetime.now(timezone.utc).isoformat()
        if metadata:
            entry["metadata"] = {**entry.get("metadata", {}), **metadata}
        return True, ""

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def summary(self) -> dict[str, int]:
        from collections import Counter
        return dict(Counter(e["state"] for e in self._data.values()))

    def entries_by_state(self, state: TSUExtractionState) -> list[str]:
        return [
            cid for cid, entry in self._data.items()
            if entry.get("state") == state.value
        ]

    def reset_failed_to_ready(self, candidate_id: str) -> tuple[bool, str]:
        current = self.get_state(candidate_id)
        if current != TSUExtractionState.FAILED:
            return False, f"cannot reset {candidate_id}: current state is {current.value}, not FAILED"
        return self.set_state(candidate_id, TSUExtractionState.READY, from_state=TSUExtractionState.FAILED)
