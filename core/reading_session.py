"""core/reading_session.py — Last-read-position persistence.

UX-007 §13 Tier C (docs/DBMA-UX-007-SessionState-Design.md §3.1). Not a
new persistence architecture — a new file reusing the "single JSON file,
overwritten atomically" pattern chat.py already established for
_CHAT_HISTORY_FILE. Deliberately kept separate from
core/research_workspace.py(ADR-004, append-only query-session log) since
"last document read" is a different concept (single latest value, not an
accumulating log) — reusing that module's schema for this would silently
widen ADR-004's scope.

Stores identifying fields only (document_id/title/source_label), no
content duplication — same rule research_workspace.py follows.
"""

from __future__ import annotations

import datetime
import json
import os
from typing import Optional

from core.config import DEFAULT_OUTPUT_DIR

_READING_DIR = os.path.join(DEFAULT_OUTPUT_DIR, "reading")
_LAST_POSITION_FILE = os.path.join(_READING_DIR, "last_position.json")


def save_last_read(document_id: str, title: str, source_label: str) -> None:
    """Persist the most recently viewed document, overwriting any prior
    entry — this module tracks one value, not a history."""
    if not document_id and not source_label:
        return

    record = {
        "document_id": document_id,
        "title": title,
        "source_label": source_label,
        "read_at": datetime.datetime.now().isoformat(timespec="seconds"),
    }
    try:
        os.makedirs(_READING_DIR, exist_ok=True)
        tmp_path = _LAST_POSITION_FILE + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False)
        os.replace(tmp_path, _LAST_POSITION_FILE)
    except OSError:
        pass


def load_last_read() -> Optional[dict]:
    """Return the last-read record, or None if none exists / unreadable."""
    if not os.path.exists(_LAST_POSITION_FILE):
        return None
    try:
        with open(_LAST_POSITION_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None
