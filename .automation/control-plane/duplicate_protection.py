"""Duplicate and conflict protection for the control plane.

Prevents:
- Duplicate task submissions (same task_id)
- Conflicting state transitions (concurrent modifications)
- Payload signature mismatches
"""
from __future__ import annotations

from typing import Any


class DuplicateError(Exception):
    """Raised when a duplicate is detected."""
    def __init__(self, task_id: str, detail: str) -> None:
        self.task_id = task_id
        super().__init__(f"Duplicate detected for {task_id}: {detail}")


class ConflictError(Exception):
    """Raised when a conflict is detected."""
    def __init__(self, task_id: str, detail: str) -> None:
        self.task_id = task_id
        super().__init__(f"Conflict detected for {task_id}: {detail}")


class DuplicateProtection:
    """Tracks submitted tasks and detects duplicates/conflicts."""

    def __init__(self):
        self._submitted_ids: dict[str, str] = {}  # task_id -> submission_timestamp
        self._payload_sigs: dict[str, str] = {}   # task_id -> payload_signature
        self._state_snapshots: dict[str, str] = {}  # task_id -> state_at_submission
        self._conflict_log: list[dict[str, Any]] = []

    def check_duplicate(self, task_id: str) -> tuple[bool, str | None]:
        """Check if a task_id has already been submitted. Returns (is_unique, duplicate_reason)."""
        if task_id in self._submitted_ids:
            reason = f"task_id {task_id} was previously submitted at {self._submitted_ids[task_id]}"
            return (False, reason)
        return (True, None)

    def register_submission(self, task_id: str, timestamp: str, payload_signature: str, state: str) -> tuple[bool, str]:
        """Register a task submission. Returns (success, message)."""
        is_unique, dup_reason = self.check_duplicate(task_id)
        if not is_unique:
            return (False, dup_reason)

        self._submitted_ids[task_id] = timestamp
        self._payload_sigs[task_id] = payload_signature
        self._state_snapshots[task_id] = state
        return (True, f"submission registered for {task_id}")

    def check_payload_integrity(self, task_id: str, new_signature: str) -> tuple[bool, str | None]:
        """Check if a new payload matches the original submission. Returns (is_valid, mismatch_reason)."""
        if task_id not in self._payload_sigs:
            return (True, None)  # No prior submission to compare against

        if new_signature != self._payload_sigs[task_id]:
            reason = f"payload_signature mismatch for {task_id}"
            self._conflict_log.append({
                "task_id": task_id,
                "type": "PAYLOAD_MISMATCH",
                "original": self._payload_sigs[task_id][:50],
                "new": new_signature[:50],
            })
            return (False, reason)
        return (True, None)

    def check_state_conflict(self, task_id: str, new_state: str) -> tuple[bool, str | None]:
        """Check if a state transition conflicts with the snapshot. Returns (ok, conflict_reason)."""
        if task_id not in self._state_snapshots:
            return (True, None)

        original_state = self._state_snapshots[task_id]
        if original_state == new_state:
            reason = f"state unchanged for {task_id}: {original_state}"
            self._conflict_log.append({
                "task_id": task_id,
                "type": "STATE_UNCHANGED",
                "state": original_state,
            })
            return (False, reason)
        return (True, None)

    def check_all(self, task_id: str, payload_signature: str, state: str) -> tuple[bool, list[str]]:
        """Run all duplicate/conflict checks. Returns (ok, list_of_issues)."""
        issues: list[str] = []

        ok1, r1 = self.check_duplicate(task_id)
        if not ok1:
            issues.append(r1)

        ok2, r2 = self.check_payload_integrity(task_id, payload_signature)
        if not ok2:
            issues.append(r2)

        ok3, r3 = self.check_state_conflict(task_id, state)
        if not ok3:
            issues.append(r3)

        return (len(issues) == 0, issues)

    @property
    def conflict_log(self) -> list[dict[str, Any]]:
        return list(self._conflict_log)

    @property
    def registered_tasks(self) -> list[str]:
        return list(self._submitted_ids.keys())
