"""core/extraction_failures.py — Persistent tracking of pre-identity
processing failures.

[SPRINT21-H-1] document_id/file_hash are generated only after extraction
and noise-cleaning succeed (core/processing.py::process_one_file(), Point
A). A failure before that point (extraction exception, empty extraction,
empty cleaned text) has no document_id yet, so it cannot live in
core/identity_registry.py's document_id-keyed documents.json — there is no
key to store it under. Previously these failures were visible only in the
single Streamlit run's UI expander (report()/logs) and, for exceptions,
Python's logger — never persisted, never queryable in a later session.

This module is a separate, append-only failure log — documents.json is
never touched by anything here. Same atomic-write pattern as
identity_registry.py::save_identity_registry() (.tmp + os.replace).
"""

from __future__ import annotations

import datetime
import json
import os
from typing import Any


def _failures_path(output_dir: str) -> str:
    return os.path.join(output_dir, "registry", "extraction_failures.json")


def load_extraction_failures(output_dir: str) -> dict[str, Any]:
    """Load the failure log. Creates-empty-in-memory if not present or
    unreadable — never raises."""
    path = _failures_path(output_dir)
    if not os.path.exists(path):
        return {"failures": []}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data.get("failures"), list):
            return {"failures": []}
        return data
    except (json.JSONDecodeError, OSError):
        return {"failures": []}


def record_extraction_failure(
    output_dir: str,
    source_file: str,
    stage: str,
    reason: str,
    retry_count: int = 0,
) -> bool:
    """Append one failure entry and persist atomically.

    Args:
        output_dir: Same output_dir process_one_file() was called with.
        source_file: Original filename (no document_id exists to key by).
        stage: "extract" | "noise" | "exception" — where it failed.
        reason: Human-readable cause (exception message or empty-text note).
        retry_count: How many _retry_with_backoff attempts were made.

    Returns:
        True on success, False on failure — never raises. A failure to
        record a failure must not mask or interrupt the original error
        path in process_one_file().
    """
    try:
        data = load_extraction_failures(output_dir)
        data["failures"].append({
            "source_file": source_file,
            "failed_at": datetime.datetime.now().isoformat(timespec="seconds"),
            "stage": stage,
            "reason": reason,
            "retry_count": retry_count,
        })

        path = _failures_path(output_dir)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp_path = path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, path)
        return True
    except Exception:
        return False
