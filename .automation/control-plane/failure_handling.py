"""Safe failure handling for the control plane.

Routes failed tasks to appropriate queues without automatic retry.
Preserves evidence and state for human review.
"""
from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class FailureHandler:
    """Handles task failures safely - no automatic retry."""

    FAILURE_CATEGORIES = {
        "VALIDATION_FAILED": "Task failed schema or gateway validation",
        "EXECUTION_ERROR": "Executor returned non-zero exit code",
        "TIMEOUT": "Task exceeded max_runtime_s",
        "POLICY_VIOLATION": "Task violated control plane policy",
        "DUPLICATE_DETECTED": "Duplicate task_id detected",
        "PAYLOAD_MISMATCH": "Payload signature mismatch",
        "TERMINAL_STATE_VIOLATION": "Illegal terminal state transition attempted",
        "STALE_WORKER": "Worker heartbeat timeout",
        "DEPENDENCY_FAILED": "Dependency task failed, blocking this task",
        "UNKNOWN": "Unclassified failure",
    }

    def __init__(self, review_queue_dir: Path | None = None):
        self._review_queue_dir = review_queue_dir or Path("/tmp/np-control-plane-review")
        self._review_queue_dir.mkdir(parents=True, exist_ok=True)
        self._failure_log: list[dict[str, Any]] = []

    def handle_failure(
        self,
        task_id: str,
        failure_code: str,
        task_data: dict[str, Any] | None = None,
        evidence_entries: list[dict[str, Any]] | None = None,
        reason: str = "",
    ) -> tuple[bool, str]:
        """Handle a task failure safely. Routes to review queue. No retry."""
        category = self._classify_failure(failure_code)
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")

        failure_record = {
            "task_id": task_id,
            "failure_code": failure_code,
            "category": category,
            "reason": reason,
            "timestamp": timestamp,
            "evidence_count": len(evidence_entries) if evidence_entries else 0,
        }

        # Route to review queue (no automatic retry)
        review_file = self._review_queue_dir / f"{task_id}-FAILED.json"
        if task_data:
            task_data["automation"] = {
                "state": "FAILED",
                "failure_code": failure_code,
                "last_transition_id": f"{task_id}#{timestamp}",
                "review_routed_at": timestamp,
            }
            review_file.write_text(
                __import__("json").dumps(task_data, ensure_ascii=False, indent=1),
                encoding="utf-8",
            )

        self._failure_log.append(failure_record)
        return (True, f"task {task_id} routed to review queue (category={category})")

    def _classify_failure(self, failure_code: str) -> str:
        for code, category in self.FAILURE_CATEGORIES.items():
            if code in failure_code or category.lower().replace(" ", "_") == failure_code.lower():
                return category
        return self.FAILURE_CATEGORIES["UNKNOWN"]

    def get_failure_log(self) -> list[dict[str, Any]]:
        return list(self._failure_log)

    def get_review_queue_files(self) -> list[str]:
        return [f.name for f in sorted(self._review_queue_dir.glob("*.json"))]

    @property
    def failure_count(self) -> int:
        return len(self._failure_log)
