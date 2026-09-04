"""Evidence collection for the control plane.

Collects, validates, and stores evidence entries for all task transitions.
Evidence is stored in jsonl format, one entry per line.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class EvidenceCollector:
    """Collects and manages evidence entries for task transitions."""

    def __init__(self, evidence_dir: Path | None = None):
        # Default is the project's real, append-only evidence store -- NOT
        # /tmp -- so this collector writes to the same place the isolated
        # n8n gateway and pilot_executor.py already use, unless a caller
        # explicitly overrides it (tests always do, with a tmp dir).
        self._evidence_dir = evidence_dir or (
            Path(__file__).resolve().parents[2] / ".automation" / "evidence"
        )
        self._evidence_dir.mkdir(parents=True, exist_ok=True)
        self._entries: list[dict[str, Any]] = []

    @property
    def evidence_dir(self) -> Path:
        return self._evidence_dir

    def collect_entry(self, entry: dict[str, Any]) -> tuple[bool, str]:
        """Collect a single evidence entry. Returns (success, message)."""
        required_fields = {"transition_id", "task_id", "from", "to"}
        for field in required_fields:
            if field not in entry:
                return (False, f"evidence entry missing required field: {field}")

        task_id = entry["task_id"]
        ev_path = self._evidence_dir / f"{task_id}.jsonl"

        # Write to file
        with ev_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")

        # Keep in memory
        self._entries.append(entry)
        return (True, f"evidence collected for {task_id}: {entry['from']} -> {entry['to']}")

    def collect_batch(self, entries: list[dict[str, Any]]) -> tuple[int, int, list[str]]:
        """Collect multiple evidence entries. Returns (success_count, fail_count, errors)."""
        success = 0
        fail = 0
        errors: list[str] = []
        for entry in entries:
            ok, msg = self.collect_entry(entry)
            if ok:
                success += 1
            else:
                fail += 1
                errors.append(msg)
        return (success, fail, errors)

    def get_entries(self, task_id: str | None = None) -> list[dict[str, Any]]:
        """Get all evidence entries. Optionally filter by task_id."""
        if task_id is None:
            return list(self._entries)
        return [e for e in self._entries if e.get("task_id") == task_id]

    def verify_completeness(self, task_id: str, required_transitions: list[tuple[str, str]]) -> tuple[bool, list[str]]:
        """Verify that all required transitions are present in evidence.

        Args:
            task_id: The task to verify.
            required_transitions: List of (from_state, to_state) pairs expected.

        Returns:
            (is_complete, list_of_missing_transitions)
        """
        entries = self.get_entries(task_id)
        actual_transitions = [(e["from"], e["to"]) for e in entries]
        missing = []
        for from_s, to_s in required_transitions:
            if (from_s, to_s) not in actual_transitions:
                missing.append(f"{from_s} -> {to_s}")
        return (len(missing) == 0, missing)

    def get_evidence_file_path(self, task_id: str) -> Path:
        """Get the path to a task's evidence file."""
        return self._evidence_dir / f"{task_id}.jsonl"

    @property
    def entry_count(self) -> int:
        return len(self._entries)
