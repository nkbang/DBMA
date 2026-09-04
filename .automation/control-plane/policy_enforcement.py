"""Executor policy enforcement.

Enforces all governance policies for task execution:
- Task type allowlist
- Namespace isolation
- Production mutation prohibition
- Scope validation
- Phase restrictions
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


class PolicyViolation(Exception):
    """Raised when a policy violation is detected."""
    def __init__(self, task_id: str, policy: str, detail: str) -> None:
        self.task_id = task_id
        self.policy = policy
        self.detail = detail
        super().__init__(f"[{policy}] {task_id}: {detail}")


class PolicyEnforcement:
    """Central policy enforcement for the control plane."""

    # Executor isolation allowlist (per CONTROL-PLANE-GENERALIZATION-001)
    ALLOWED_TASK_TYPES = {"pilot_echo"}
    REQUIRED_NAMESPACE = "control-plane-pilot"

    def __init__(self, strict: bool = True):
        self.strict = strict
        self._violations: list[dict[str, Any]] = []

    def check_task_isolation(self, task: dict[str, Any]) -> tuple[bool, str | None]:
        """Check task isolation contract (G3/G8). Returns (ok, failure_reason)."""
        task_id = task.get("task_id", "unknown")

        # Check task_type against allowlist
        task_type = task.get("task_type", "")
        if task_type not in self.ALLOWED_TASK_TYPES:
            reason = f"task_type '{task_type}' not in ALLOWED_TASK_TYPES {self.ALLOWED_TASK_TYPES}"
            self._record_violation(task_id, "ISOLATION", reason)
            return (False, reason)

        # Check namespace
        scope = task.get("scope", {})
        namespace = scope.get("namespace", "")
        if namespace != self.REQUIRED_NAMESPACE:
            reason = f"namespace '{namespace}' != required '{self.REQUIRED_NAMESPACE}'"
            self._record_violation(task_id, "NAMESPACE", reason)
            return (False, reason)

        # Check production_mutation
        if task.get("production_mutation") is True:
            reason = "production_mutation must be false"
            self._record_violation(task_id, "PRODUCTION_MUTATION", reason)
            return (False, reason)

        return (True, None)

    def check_scope_paths(self, task: dict[str, Any]) -> tuple[bool, str | None]:
        """Check that scope.allowed_paths does not reference production paths."""
        task_id = task.get("task_id", "unknown")
        scope = task.get("scope", {})
        allowed_paths = scope.get("allowed_paths", [])

        PRODUCTION_PATHS = [
            "core/retrieval.py",
            "NAE/pipeline/registration/",
            "data/",
            ".automation/tasks/schema.json",
        ]

        for path in allowed_paths:
            for prod_path in PRODUCTION_PATHS:
                if prod_path in path:
                    reason = f"allowed_paths contains production path: {path}"
                    self._record_violation(task_id, "SCOPE_PATH", reason)
                    return (False, reason)

        return (True, None)

    def check_phase_restrictions(self, task: dict[str, Any]) -> tuple[bool, str | None]:
        """Check phase-specific restrictions."""
        task_id = task.get("task_id", "unknown")
        phase = task.get("phase", "")

        if phase == "PILOT":
            if task.get("production_mutation") is True:
                reason = "PILOT phase cannot have production_mutation=true"
                self._record_violation(task_id, "PHASE_RESTRICTION", reason)
                return (False, reason)

        return (True, None)

    def check_all(self, task: dict[str, Any]) -> tuple[bool, list[str]]:
        """Run all policy checks. Returns (ok, list_of_violations)."""
        violations: list[str] = []

        ok1, r1 = self.check_task_isolation(task)
        if not ok1:
            violations.append(r1)

        ok2, r2 = self.check_scope_paths(task)
        if not ok2:
            violations.append(r2)

        ok3, r3 = self.check_phase_restrictions(task)
        if not ok3:
            violations.append(r3)

        return (len(violations) == 0, violations)

    def _record_violation(self, task_id: str, policy: str, detail: str) -> None:
        self._violations.append({
            "task_id": task_id,
            "policy": policy,
            "detail": detail,
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        })

    @property
    def violations(self) -> list[dict[str, Any]]:
        return list(self._violations)
