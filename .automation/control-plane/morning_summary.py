"""Morning summary generation for the control plane.

Generates a comprehensive summary of all night-shift activities:
- Task execution statistics
- Success/failure breakdown
- Evidence completeness report
- Policy violation summary
- Stale worker report
- Review queue status
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


class MorningSummary:
    """Generates a morning summary of night-shift activities."""

    def __init__(self):
        self._summary_data: dict[str, Any] = {}

    def generate(
        self,
        total_tasks: int = 0,
        completed: int = 0,
        failed: int = 0,
        validated_only: int = 0,
        skipped: int = 0,
        review_queue_count: int = 0,
        stale_workers: list[str] | None = None,
        policy_violations: list[dict[str, Any]] | None = None,
        evidence_summary: dict[str, Any] | None = None,
        dependency_graph_status: str = "N/A",
        terminal_violations: list[dict[str, Any]] | None = None,
        duplicate_prevented: int = 0,
        execution_times: list[float] | None = None,
    ) -> dict[str, Any]:
        """Generate a comprehensive morning summary."""
        stale_workers = stale_workers or []
        policy_violations = policy_violations or []
        evidence_summary = evidence_summary or {}
        terminal_violations = terminal_violations or []
        execution_times = execution_times or []

        avg_time = sum(execution_times) / len(execution_times) if execution_times else 0
        max_time = max(execution_times) if execution_times else 0
        min_time = min(execution_times) if execution_times else 0

        self._summary_data = {
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "summary": {
                "total_tasks_processed": total_tasks,
                "completed": completed,
                "failed": failed,
                "validated_only": validated_only,
                "skipped": skipped,
                "success_rate": f"{(completed / total_tasks * 100):.1f}%" if total_tasks > 0 else "N/A",
            },
            "review_queue": {
                "count": review_queue_count,
                "status": "EMPTY" if review_queue_count == 0 else "HAS_ITEMS",
            },
            "stale_workers": {
                "count": len(stale_workers),
                "workers": stale_workers,
            },
            "policy_violations": {
                "count": len(policy_violations),
                "details": policy_violations,
            },
            "evidence": evidence_summary,
            "dependency_graph": {
                "status": dependency_graph_status,
            },
            "terminal_state_enforcement": {
                "violations_detected": len(terminal_violations),
                "details": terminal_violations,
            },
            "duplicate_protection": {
                "duplicates_prevented": duplicate_prevented,
            },
            "execution_performance": {
                "avg_time_s": round(avg_time, 3),
                "max_time_s": round(max_time, 3),
                "min_time_s": round(min_time, 3),
                "sample_count": len(execution_times),
            },
        }
        return self._summary_data

    def format_text(self) -> str:
        """Format the summary as human-readable text."""
        if not self._summary_data:
            return "No summary data available."

        lines = [
            "=" * 60,
            "NAE AUTONOMOUS NIGHT-SHIFT MORNING SUMMARY",
            "=" * 60,
            f"Generated at: {self._summary_data['generated_at']}",
            "",
            "--- Task Statistics ---",
            f"Total tasks processed: {self._summary_data['summary']['total_tasks_processed']}",
            f"Completed:             {self._summary_data['summary']['completed']}",
            f"Failed:                {self._summary_data['summary']['failed']}",
            f"Validated only:        {self._summary_data['summary']['validated_only']}",
            f"Skipped:               {self._summary_data['summary']['skipped']}",
            f"Success rate:          {self._summary_data['summary']['success_rate']}",
            "",
            "--- Review Queue ---",
            f"Items in review queue: {self._summary_data['review_queue']['count']}",
            "",
            "--- Stale Workers ---",
            f"Stale worker count:    {self._summary_data['stale_workers']['count']}",
        ]
        for w in self._summary_data['stale_workers']['workers']:
            lines.append(f"  - {w}")
        lines.extend([
            "",
            "--- Policy Violations ---",
            f"Violations detected:   {self._summary_data['policy_violations']['count']}",
            "",
            "--- Terminal State Enforcement ---",
            f"Violations detected:   {self._summary_data['terminal_state_enforcement']['violations_detected']}",
            "",
            "--- Duplicate Protection ---",
            f"Duplicates prevented:  {self._summary_data['duplicate_protection']['duplicates_prevented']}",
            "",
            "--- Execution Performance ---",
            f"Avg execution time:    {self._summary_data['execution_performance']['avg_time_s']}s",
            f"Max execution time:    {self._summary_data['execution_performance']['max_time_s']}s",
            f"Min execution time:    {self._summary_data['execution_performance']['min_time_s']}s",
            "",
            "=" * 60,
        ])
        return "\n".join(lines)

    @property
    def data(self) -> dict[str, Any]:
        return self._summary_data
