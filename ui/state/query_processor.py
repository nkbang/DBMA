"""ui/state/query_processor.py — Shared QueryProcessor accessor with TSU
dataset staleness detection.

[SPRINT21-G Gap#1] QueryProcessor (and the RetrievalEngine it owns) was
cached in st.session_state for the whole browser session
("shared_query_processor", one RetrievalEngine instance per session — see
ui/pages/chat.py, ui/pages/research.py). RetrievalEngine loads the TSU
corpus into memory once at construction (core/retrieval.py::_load_corpus).
If Processing -> reconcile_pending() updated the TSU dataset on disk
*after* a session's processor was already created, that session kept
serving the stale in-memory corpus indefinitely — newly indexed documents
were invisible to Chat/Research until a full browser reload. Confirmed via
code trace during SPRINT21-G Preflight (no staleness check existed).

Fix: read the TSU manifest's dataset_sha256 (already computed by
write_manifest() on every reconcile — no extra hashing here) on each
access and recreate the QueryProcessor whenever it changes.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import streamlit as st

from core.config import DEFAULT_TSU_MANIFEST_PATH
from core.retrieval import QueryProcessor

_SESSION_KEY = "shared_query_processor"
_FINGERPRINT_KEY = "shared_query_processor_dataset_sha256"
_LATENCY_KEY = "query_latencies_ms"
_LATENCY_HISTORY_CAP = 200


def _current_dataset_fingerprint() -> Optional[str]:
    manifest_path = Path(DEFAULT_TSU_MANIFEST_PATH)
    if not manifest_path.exists():
        return None
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        return data.get("dataset_sha256")
    except (json.JSONDecodeError, OSError):
        return None


def get_shared_query_processor() -> QueryProcessor:
    """One RetrievalEngine instance per session, recreated whenever the
    TSU dataset on disk has changed since it was created.

    Manifest missing/unreadable does not force a recreate on every call
    (fingerprint stays None across calls, comparing equal) — avoids
    rebuilding the processor repeatedly on a transient read failure.
    """
    fingerprint = _current_dataset_fingerprint()
    cached_fingerprint = st.session_state.get(_FINGERPRINT_KEY)

    if _SESSION_KEY not in st.session_state or (
        fingerprint is not None and fingerprint != cached_fingerprint
    ):
        st.session_state[_SESSION_KEY] = QueryProcessor()
        st.session_state[_FINGERPRINT_KEY] = fingerprint

    return st.session_state[_SESSION_KEY]


def record_query_latency(total_ms: float) -> None:
    """Append one QueryProcessor.process() call's total_ms to this
    session's running history — Monitor's "평균 응답 시간" card reads
    session_state[_LATENCY_KEY] directly (same key). Capped so a long
    session doesn't grow this list unbounded."""
    history = st.session_state.setdefault(_LATENCY_KEY, [])
    history.append(total_ms)
    if len(history) > _LATENCY_HISTORY_CAP:
        del history[: len(history) - _LATENCY_HISTORY_CAP]
