"""Task Queue Contract - schema validation, state machine, queue management.

This module defines the canonical task contract used by the control plane.
It does NOT modify .automation/tasks/schema.json (Approved under ADR-022).
All validation is additive and isolated to this module.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


class TaskState(str, Enum):
    """Valid task states in the control plane state machine."""
    IDLE = "IDLE"
    RECEIVED = "RECEIVED"
    VALIDATION_PASSED = "VALIDATION_PASSED"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    IN_REVIEW = "IN_REVIEW"

    def is_terminal(self) -> bool:
        return self in (TaskState.COMPLETED, TaskState.FAILED)

    def is_active(self) -> bool:
        return not self.is_terminal()


LEGAL_TRANSITIONS: dict[TaskState, frozenset[TaskState]] = {
    TaskState.IDLE: frozenset({TaskState.RECEIVED}),
    TaskState.RECEIVED: frozenset({TaskState.VALIDATION_PASSED, TaskState.FAILED}),
    TaskState.VALIDATION_PASSED: frozenset({
        TaskState.PENDING_APPROVAL, TaskState.QUEUED,
        TaskState.PROCESSING, TaskState.FAILED,
    }),
    TaskState.PENDING_APPROVAL: frozenset({TaskState.QUEUED, TaskState.FAILED}),
    TaskState.QUEUED: frozenset({TaskState.PROCESSING, TaskState.FAILED}),
    TaskState.PROCESSING: frozenset({TaskState.COMPLETED, TaskState.FAILED}),
    TaskState.COMPLETED: frozenset(),
    TaskState.FAILED: frozenset(),
    TaskState.IN_REVIEW: frozenset({TaskState.QUEUED, TaskState.COMPLETED}),
}

REQUIRED_FIELDS_BY_PHASE: dict[str, list[str]] = {
    "PILOT": [
        "schema_version", "task_id", "title", "owner", "state",
        "phase", "task_type", "scope", "authorized_by",
        "production_mutation", "constraints", "automation",
    ],
    "PRODUCTION": [
        "schema_version", "task_id", "title", "owner", "state",
        "phase", "task_type", "scope", "authorized_by",
        "production_mutation", "constraints", "automation",
        "requires_human_approval",
    ],
}


def validate_task_schema(task: dict[str, Any]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    phase = task.get("phase", "")
    required = REQUIRED_FIELDS_BY_PHASE.get(phase, REQUIRED_FIELDS_BY_PHASE["PILOT"])
    for field in required:
        if field not in task:
            errors.append(f"missing required field: {field}")
    task_id = task.get("task_id", "")
    if not isinstance(task_id, str) or not task_id.strip():
        errors.append("task_id must be a non-empty string")
    state = task.get("state", "")
    try:
        TaskState(state)
    except ValueError:
        errors.append(f"invalid state: {state!r}")
    if phase not in ("PILOT", "PRODUCTION"):
        errors.append(f"invalid phase: {phase!r}")
    pm = task.get("production_mutation")
    if pm is True:
        errors.append("production_mutation must be false in PILOT phase")
    scope = task.get("scope")
    if not isinstance(scope, dict):
        errors.append("scope must be a dict")
    else:
        ns = scope.get("namespace")
        if not isinstance(ns, str) or not ns.strip():
            errors.append("scope.namespace must be a non-empty string")
    tt = task.get("task_type")
    if not isinstance(tt, str) or not tt.strip():
        errors.append("task_type must be a non-empty string")
    constraints = task.get("constraints")
    if not isinstance(constraints, dict):
        errors.append("constraints must be a dict")
    else:
        max_rt = constraints.get("max_runtime_s")
        if max_rt is not None and (not isinstance(max_rt, (int, float)) or max_rt <= 0):
            errors.append("constraints.max_runtime_s must be a positive number")
    auto = task.get("automation")
    if not isinstance(auto, dict):
        errors.append("automation must be a dict")
    else:
        auto_state = auto.get("state")
        if auto_state is not None:
            try:
                TaskState(auto_state)
            except ValueError:
                errors.append(f"invalid automation.state: {auto_state!r}")
    audit = task.get("audit")
    if audit is not None and not isinstance(audit, dict):
        errors.append("audit must be a dict or null")
    return (len(errors) == 0, errors)


def enforce_transition(current_state: TaskState, target_state: TaskState) -> tuple[bool, str]:
    if current_state.is_terminal():
        return (False, f"terminal state {current_state.value} - no outgoing transitions allowed")
    allowed = LEGAL_TRANSITIONS.get(current_state, frozenset())
    if target_state not in allowed:
        return (False, f"{current_state.value} -> {target_state.value} is not a legal transition")
    return (True, "transition is legal")


def generate_transition_id(task_id: str, execution_id: str | None = None) -> str:
    if execution_id is None:
        execution_id = str(uuid.uuid4())
    return f"{task_id}#{execution_id}"


def compute_payload_signature(task_id: str, evidence_dir: Path) -> str:
    """Read the canonical payload_signature from the last evidence entry for task_id.

    This function does NOT recompute a signature from the task dict.
    It propagates the value the gateway (n8n) already established,
    preventing cross-runtime signature drift.

    See .automation/night-shift/pilot_executor.py::read_canonical_payload_signature()
    for the canonical reference implementation.
    """
    ev_path = evidence_dir / f"{task_id}.jsonl"
    if not ev_path.exists():
        raise RuntimeError(
            f"no evidence file found for {task_id} at {ev_path}; cannot propagate signature"
        )
    lines = [l for l in ev_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    if not lines:
        raise RuntimeError(
            f"no evidence entries found for {task_id}; cannot propagate signature"
        )
    last_entry = json.loads(lines[-1])
    sig = last_entry.get("payload_signature")
    if not sig:
        raise RuntimeError(
            f"last evidence entry for {task_id} has no payload_signature"
        )
    return sig


def verify_payload_signature(task_id: str, evidence_dir: Path, signature: str) -> bool:
    return compute_payload_signature(task_id, evidence_dir) == signature


class TaskQueue:
    """In-memory task queue with filesystem persistence."""

    def __init__(self, queue_dir: Path | None = None):
        self._queue: list[dict[str, Any]] = []
        self._insertion_order: list[str] = []
        self._queue_dir = queue_dir or Path("/tmp/np-control-plane-queue")
        self._queue_dir.mkdir(parents=True, exist_ok=True)

    def add(self, task: dict[str, Any]) -> tuple[bool, str]:
        is_valid, errors = validate_task_schema(task)
        if not is_valid:
            return (False, f"schema validation failed: {'; '.join(errors)}")
        task_id = task["task_id"]
        if task_id in self._insertion_order:
            return (False, f"duplicate task_id in queue: {task_id}")
        task_file = self._queue_dir / f"{task_id}.json"
        task_file.write_text(json.dumps(task, ensure_ascii=False, indent=1), encoding="utf-8")
        self._queue.append(task)
        self._insertion_order.append(task_id)
        return (True, f"task {task_id} added to queue")

    def dequeue(self) -> dict[str, Any] | None:
        if not self._queue:
            return None
        task = self._queue.pop(0)
        self._insertion_order.pop(0)
        return task

    def peek(self) -> dict[str, Any] | None:
        return self._queue[0] if self._queue else None

    @property
    def depth(self) -> int:
        return len(self._queue)

    @property
    def task_ids(self) -> list[str]:
        return list(self._insertion_order)

    def contains(self, task_id: str) -> bool:
        return task_id in self._insertion_order

    def remove(self, task_id: str) -> bool:
        if task_id not in self._insertion_order:
            return False
        idx = self._insertion_order.index(task_id)
        self._queue.pop(idx)
        self._insertion_order.pop(idx)
        return True

    def all_tasks(self) -> list[dict[str, Any]]:
        return list(self._queue)


def make_evidence_entry(
    task_id: str,
    from_state: str,
    to_state: str,
    failure_code: str | None = None,
    payload_signature: str | None = None,
    execution_id: str | None = None,
    reason: str = "",
    actor: str = "control-plane",
) -> dict[str, Any]:
    """Create a canonical evidence entry for a state transition."""
    if execution_id is None:
        execution_id = str(uuid.uuid4())
    return {
        "transition_id": generate_transition_id(task_id, execution_id),
        "task_id": task_id,
        "from": from_state,
        "to": to_state,
        "failure_code": failure_code,
        "actor": actor,
        "payload_signature": payload_signature or "",
        "execution_id": execution_id,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "reason": reason,
    }
