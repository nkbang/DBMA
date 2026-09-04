"""Host executor dispatch contract.

Routes tasks to the appropriate executor based on task_type and scope.
Does NOT import or invoke any production modules.
"""
from __future__ import annotations

import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class ExecutorDispatchError(Exception):
    """Raised when executor dispatch fails."""
    def __init__(self, task_id: str, reason: str) -> None:
        self.task_id = task_id
        super().__init__(f"Executor dispatch failed for {task_id}: {reason}")


class ExecutorPolicy:
    """Defines what executors are allowed to do."""

    ALLOWED_EXECUTORS = {"pilot_echo"}
    DISALLOWED_EXECUTORS = {"production_register", "direct_qdrant", "corpus_modify"}

    @classmethod
    def is_allowed(cls, executor_type: str) -> bool:
        return executor_type in cls.ALLOWED_EXECUTORS

    @classmethod
    def is_disallowed(cls, executor_type: str) -> bool:
        return executor_type in cls.DISALLOWED_EXECUTORS


class ExecutorDispatch:
    """Dispatches tasks to the appropriate executor.

    Enforces policy before dispatch. Never invokes production code directly.
    """

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self._dispatch_log: list[dict[str, Any]] = []

    def dispatch(self, task: dict[str, Any]) -> tuple[bool, str]:
        """Dispatch a task to the appropriate executor. Returns (success, result)."""
        task_id = task.get("task_id", "unknown")
        task_type = task.get("task_type", "")
        policy = ExecutorPolicy()

        if not task_type:
            return (False, f"no task_type specified for {task_id}")

        if policy.is_disallowed(task_type):
            msg = f"executor type '{task_type}' is disallowed by policy"
            self._log_dispatch(task_id, task_type, "BLOCKED", msg)
            return (False, msg)

        if not policy.is_allowed(task_type):
            msg = f"executor type '{task_type}' is not in the allowed list"
            self._log_dispatch(task_id, task_type, "BLOCKED", msg)
            return (False, msg)

        if self.dry_run:
            msg = f"[DRY-RUN] would dispatch {task_id} to executor '{task_type}'"
            self._log_dispatch(task_id, task_type, "DRY_RUN", msg)
            return (True, msg)

        if task_type == "pilot_echo":
            return self._dispatch_pilot_echo(task_id, task)
        else:
            return (False, f"unknown executor type: {task_type}")

    def _dispatch_pilot_echo(self, task_id: str, task: dict[str, Any]) -> tuple[bool, str]:
        """Dispatch a pilot_echo task (isolated, non-production)."""
        start = time.monotonic()
        try:
            result = subprocess.run(
                ["echo", f"pilot_echo executed for {task_id}"],
                capture_output=True, text=True, timeout=30,
            )
            elapsed = time.monotonic() - start
            stdout = result.stdout.strip()
            stderr = result.stderr.strip() if result.returncode != 0 else ""
            self._log_dispatch(task_id, "pilot_echo", "COMPLETED", f"exit={result.returncode} elapsed={elapsed:.2f}s")
            return (result.returncode == 0, f"exit={result.returncode} stdout={stdout!r}")
        except subprocess.TimeoutExpired:
            self._log_dispatch(task_id, "pilot_echo", "TIMEOUT", f"exceeded 30s limit")
            return (False, "executor timeout exceeded 30s")
        except Exception as exc:
            self._log_dispatch(task_id, "pilot_echo", "ERROR", str(exc))
            return (False, f"executor error: {exc}")

    def _log_dispatch(self, task_id: str, executor_type: str, status: str, message: str) -> None:
        self._dispatch_log.append({
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "task_id": task_id,
            "executor_type": executor_type,
            "status": status,
            "message": message,
        })

    @property
    def dispatch_log(self) -> list[dict[str, Any]]:
        return list(self._dispatch_log)
