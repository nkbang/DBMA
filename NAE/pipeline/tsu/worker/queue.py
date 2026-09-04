"""TSU Extraction Exception Queue (Phase 3).

Captures failed extraction candidates for human review.
Never writes to NAE/review/human/exception_queue.json — that queue
belongs to the downstream Production human-review process and must
not be mixed with pre-TSU extraction failures.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class ExceptionEntry:
    candidate_id: str
    error_type: str
    error_message: str
    state_at_failure: str
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class TSUExtractionExceptionQueue:
    """Upstream-only exception record for failed TSU extraction candidates.

    Never writes to NAE/review/human/exception_queue.json — that queue
    belongs to the downstream/Production human-review process (ADR-020)
    and must not be mixed with pre-TSU extraction failures.
    """

    def __init__(self, path: Path | None = None):
        if path is None:
            from . import config as worker_config
            path = worker_config.DEFAULT_EXCEPTION_QUEUE_PATH
        self.path = path
        self._entries: list[dict[str, Any]] = []
        if path.exists():
            self._entries = json.loads(path.read_text(encoding="utf-8"))

    def record(
        self,
        candidate_id: str,
        error_type: str,
        error_message: str,
        state_at_failure: str,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._entries.append({
            "candidate_id": candidate_id,
            "error_type": error_type,
            "error_message": error_message,
            "state_at_failure": state_at_failure,
            "metadata": metadata or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self._entries, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def entries(self) -> list[dict[str, Any]]:
        return list(self._entries)

    def summary(self) -> dict[str, int]:
        from collections import Counter
        return dict(Counter(e["error_type"] for e in self._entries))

    def clear(self) -> None:
        """Clear all entries (requires explicit call)."""
        self._entries = []
        self.save()
