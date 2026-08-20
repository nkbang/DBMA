"""Terminal-state enforcement.

Ensures that tasks in terminal states (COMPLETED, FAILED) cannot be
transitioned out of without explicit human override.
"""
from __future__ import annotations

from typing import Any


class TerminalStateError(Exception):
    """Raised when an illegal terminal state transition is attempted."""
    def __init__(self, task_id: str, from_state: str, to_state: str) -> None:
        self.task_id = task_id
        self.from_state = from_state
        self.to_state = to_state
        super().__init__(f"Cannot transition {task_id}: {from_state} -> {to_state} (terminal state)")


class TerminalStateEnforcer:
    """Enforces terminal state boundaries for all tasks."""

    TERMINAL_STATES = {"COMPLETED", "FAILED"}

    def __init__(self):
        self._terminal_log: list[dict[str, Any]] = []

    def enforce(self, task_id: str, from_state: str, to_state: str) -> tuple[bool, str]:
        """Enforce terminal state rules. Returns (ok, message)."""
        if from_state in self.TERMINAL_STATES and from_state != to_state:
            msg = f"Cannot transition {task_id}: {from_state} -> {to_state} (terminal state)"
            self._log_violation(task_id, from_state, to_state, msg)
            raise TerminalStateError(task_id, from_state, to_state)

        if from_state == to_state:
            msg = f"No-op transition for {task_id}: {from_state} -> {to_state}"
            return (False, msg)

        self._log_transition(task_id, from_state, to_state)
        return (True, f"transition {from_state} -> {to_state} allowed for {task_id}")

    def is_terminal(self, state: str) -> bool:
        return state in self.TERMINAL_STATES

    def can_transition(self, from_state: str, to_state: str) -> bool:
        if from_state in self.TERMINAL_STATES:
            return from_state == to_state
        return True

    def _log_violation(self, task_id: str, from_state: str, to_state: str, message: str) -> None:
        self._terminal_log.append({
            "task_id": task_id,
            "from_state": from_state,
            "to_state": to_state,
            "message": message,
            "type": "TERMINAL_VIOLATION",
        })

    def _log_transition(self, task_id: str, from_state: str, to_state: str) -> None:
        self._terminal_log.append({
            "task_id": task_id,
            "from_state": from_state,
            "to_state": to_state,
            "type": "TERMINAL_OK",
        })

    @property
    def terminal_log(self) -> list[dict[str, Any]]:
        return list(self._terminal_log)
