"""Control Plane Orchestrator - integrates all control plane modules.

This is the central coordinator that ties together:
- Task Queue contract
- Dependency graph
- n8n gateway
- Executor dispatch
- Policy enforcement
- Heartbeat monitoring
- Terminal state enforcement
- Evidence collection
- Duplicate/conflict protection
- Failure handling
- Morning summary generation
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from task_contract import (
    TaskState, TaskQueue, enforce_transition,
    generate_transition_id, compute_payload_signature, make_evidence_entry,
    validate_task_schema,
)
from dependency_graph import DependencyGraph
from n8n_gateway import N8NGateway, GatewayError
from executor_dispatch import ExecutorDispatch, ExecutorPolicy
from policy_enforcement import PolicyEnforcement, PolicyViolation
from heartbeat import HeartbeatMonitor
from terminal_state import TerminalStateEnforcer, TerminalStateError
from evidence_collector import EvidenceCollector
from duplicate_protection import DuplicateProtection
from failure_handling import FailureHandler
from morning_summary import MorningSummary


class ControlPlaneError(Exception):
    """Raised when the control plane encounters a fatal error."""
    pass


class ControlPlane:
    """Main orchestrator for the autonomous night-shift control plane."""

    def __init__(
        self,
        dry_run: bool = False,
        evidence_dir: Path | None = None,
        review_queue_dir: Path | None = None,
        queue_dir: Path | None = None,
    ):
        self.dry_run = dry_run
        self.queue = TaskQueue(queue_dir)
        self.dependency_graph = DependencyGraph()
        self.gateway = N8NGateway()
        self.executor = ExecutorDispatch(dry_run=dry_run)
        self.policy = PolicyEnforcement(strict=True)
        self.heartbeat = HeartbeatMonitor(default_interval_s=60.0)
        self.terminal_enforcer = TerminalStateEnforcer()
        self.evidence = EvidenceCollector(evidence_dir)
        self.duplicate_protection = DuplicateProtection()
        self.failure_handler = FailureHandler(review_queue_dir)
        self.morning_summary = MorningSummary()
        self._execution_log: list[dict[str, Any]] = []
        self._execution_times: list[float] = []
        self._transition_counter = 0

    def _next_transition_id(self, task_id: str) -> str:
        self._transition_counter += 1
        return generate_transition_id(task_id, str(self._transition_counter))

    def submit_task(self, task: dict[str, Any]) -> tuple[bool, str]:
        """Submit a task to the control plane. Full pipeline validation."""
        import time as _time
        task_id = task.get("task_id", "unknown")
        start = _time.monotonic()

        # 1. Duplicate check (use task_id as key; real canonical sig comes from gateway)
        payload_sig = task_id  # placeholder; duplicate_protection checks by task_id anyway
        ok, issues = self.duplicate_protection.check_all(task_id, payload_sig, task.get("state", ""))
        if not ok:
            for issue in issues:
                self._log_execution(task_id, "DUPLICATE_CHECK", False, issue)
            return (False, f"duplicate/conflict detected: {'; '.join(issues)}")

        # 2. Schema validation
        is_valid, errors = validate_task_schema(task)
        if not is_valid:
            self._log_execution(task_id, "SCHEMA_VALIDATION", False, "; ".join(errors))
            return (False, f"schema validation failed: {'; '.join(errors)}")

        # 3. Policy enforcement
        ok, violations = self.policy.check_all(task)
        if not ok:
            for v in violations:
                self._log_execution(task_id, "POLICY_ENFORCEMENT", False, v)
            return (False, f"policy violation: {'; '.join(violations)}")

        # 4. Register submission
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        self.duplicate_protection.register_submission(task_id, ts, payload_sig, task.get("state", ""))

        # 5. Add to dependency graph
        deps = task.get("dependencies", [])
        self.dependency_graph.add_task(task_id, dependencies=deps)

        # 6. Add to queue
        ok, msg = self.queue.add(task)
        if not ok:
            return (False, msg)

        # 7. Establish the canonical gateway evidence entry (RECEIVED ->
        # VALIDATION_PASSED) NOW, at submission time -- mirroring the real
        # flow where n8n's webhook writes this entry before the executor
        # ever runs. This guarantees compute_payload_signature() always has
        # something to read later in process_next(), rather than depending
        # on a real n8n call having happened first (which dry_run mode
        # never makes). The signature covers only {"task_id": ...} -- the
        # same minimal envelope this project's real n8n webhook is always
        # POSTed with (see .automation/night-shift/pilot_executor.py and
        # every curl example throughout this project) -- not the full task
        # dict, so a real gateway's JS JSON.stringify(webhook body) would
        # match this Python json.dumps({"task_id": ...}) byte-for-byte.
        gateway_signature = json.dumps({"task_id": task_id}, separators=(",", ":"))
        self.evidence.collect_entry({
            "transition_id": self._next_transition_id(task_id),
            "task_id": task_id, "from": "RECEIVED", "to": "VALIDATION_PASSED",
            "failure_code": None,
            "actor": "control_plane_gateway_stub" if self.dry_run else "control_plane_gateway",
            "payload_signature": gateway_signature,
            "execution_id": str(self._transition_counter),
            "timestamp": ts,
            "reason": "control plane accepted task at submission",
        })

        elapsed = _time.monotonic() - start
        self._log_execution(task_id, "SUBMIT", True, f"submitted to queue ({elapsed:.3f}s)")
        return (True, msg)

    def process_next(self) -> dict[str, Any]:
        import time as _time
        task = self.queue.dequeue()
        if task is None:
            return {"status": "EMPTY", "message": "queue is empty"}
        task_id = task["task_id"]
        start = _time.monotonic()
        try:
            current_state = TaskState(task.get("state", "IDLE"))
            ok, msg = self.terminal_enforcer.enforce(task_id, current_state.value, TaskState.PROCESSING.value)
            if not ok:
                return {"status": "BLOCKED", "task_id": task_id, "reason": msg}
            self.dependency_graph.update_state(task_id, current_state.value)
            ready = self.dependency_graph.get_ready_tasks()
            if task_id not in ready:
                return {"status": "BLOCKED", "task_id": task_id, "reason": "dependencies not met"}
            stale = self.heartbeat.detect_stale_workers()
            if stale:
                for w in stale:
                    self._log_execution(task_id, "HEARTBEAT", False, f"stale worker: {w}")
            if not self.dry_run:
                try:
                    http_code, response = self.gateway.post_task(task)
                    valid, verify_errors = self.gateway.verify_response(response, task_id)
                    if not valid:
                        for e in verify_errors:
                            self._log_execution(task_id, "GATEWAY_VERIFY", False, e)
                except GatewayError as exc:
                    self._log_execution(task_id, "GATEWAY_ERROR", False, str(exc))
                    return {"status": "GATEWAY_ERROR", "task_id": task_id, "reason": str(exc)}
            result = self.executor.dispatch(task)
            ok, msg = result
            # Fresh execution_id (via _next_transition_id) -- this entry is a
            # DIFFERENT transition than the SUBMIT-time RECEIVED->
            # VALIDATION_PASSED entry, so it must not share that entry's
            # transition_id. (This exact sharing bug was found and fixed in
            # CUE's pilot_executor.py last round; do not reintroduce it.)
            self._next_transition_id(task_id)
            evidence_entry = make_evidence_entry(
                task_id=task_id, from_state=current_state.value,
                to_state="COMPLETED" if ok else "FAILED",
                failure_code=None if ok else "EXECUTION_ERROR",
                payload_signature=compute_payload_signature(task_id, self.evidence.evidence_dir),
                execution_id=str(self._transition_counter), reason=msg,
            )
            self.evidence.collect_entry(evidence_entry)
            final_state = "COMPLETED" if ok else "FAILED"
            self.dependency_graph.update_state(task_id, final_state)
            elapsed = _time.monotonic() - start
            self._execution_times.append(elapsed)
            self._log_execution(task_id, "PROCESS", ok, f"{current_state.value} -> {final_state} ({elapsed:.3f}s)")
            return {
                "status": "COMPLETED" if ok else "FAILED",
                "task_id": task_id, "from_state": current_state.value,
                "to_state": final_state, "evidence_entry": evidence_entry,
                "execution_time_s": round(elapsed, 3),
            }
        except TerminalStateError as exc:
            elapsed = _time.monotonic() - start
            self._log_execution(task_id, "TERMINAL_VIOLATION", False, str(exc))
            return {"status": "TERMINAL_ERROR", "task_id": task_id, "reason": str(exc)}
        except PolicyViolation as exc:
            elapsed = _time.monotonic() - start
            self._log_execution(task_id, "POLICY_VIOLATION", False, str(exc))
            return {"status": "POLICY_ERROR", "task_id": task_id, "reason": str(exc)}
        except Exception as exc:
            elapsed = _time.monotonic() - start
            self._log_execution(task_id, "UNEXPECTED_ERROR", False, str(exc))
            return {"status": "ERROR", "task_id": task_id, "reason": str(exc)}

    def handle_failure(self, task: dict[str, Any], failure_code: str, reason: str = "") -> tuple[bool, str]:
        task_id = task.get("task_id", "unknown")
        evidence = self.evidence.get_entries(task_id)
        return self.failure_handler.handle_failure(
            task_id=task_id, failure_code=failure_code,
            task_data=task, evidence_entries=evidence, reason=reason,
        )

    def generate_morning_summary(self) -> dict[str, Any]:
        stale = self.heartbeat.detect_stale_workers()
        # Count unique tasks, not log entries (each task has SUBMIT + PROCESS entries)
        unique_tasks = set(e["task_id"] for e in self._execution_log)
        completed = sum(1 for t in unique_tasks
                        if any(e.get("ok") and e["action"] == "PROCESS"
                               for e in self._execution_log if e["task_id"] == t))
        failed = sum(1 for t in unique_tasks
                     if any(not e.get("ok") and e["action"] == "PROCESS"
                            for e in self._execution_log if e["task_id"] == t))
        return self.morning_summary.generate(
            total_tasks=len(unique_tasks),
            completed=completed,
            failed=failed,
            review_queue_count=self.failure_handler.failure_count,
            stale_workers=stale,
            policy_violations=self.policy.violations,
            evidence_summary={
                "total_entries": self.evidence.entry_count,
                "unique_tasks": len(set(e["task_id"] for e in self.evidence.get_entries())),
            },
            dependency_graph_status="CYCLE_FREE" if self.dependency_graph.topological_sort() else "HAS_CYCLE",
            terminal_violations=self.terminal_enforcer.terminal_log,
            duplicate_prevented=len(self.duplicate_protection.conflict_log),
            execution_times=self._execution_times,
        )

    def _log_execution(self, task_id: str, action: str, ok: bool, message: str) -> None:
        self._execution_log.append({
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "task_id": task_id, "action": action, "ok": ok, "message": message,
        })

    @property
    def execution_log(self) -> list[dict[str, Any]]:
        return list(self._execution_log)
