"""ui/state/background_builder.py — Shared BackgroundIndexBuilder accessor.

DBMA-SEARCH-INFRA-001 HQ 제안 ⑧. Same singleton pattern as
ui/state/query_processor.py::get_shared_query_processor(), but using
st.cache_resource (not session_state) — the background worker thread must
survive across Streamlit reruns AND across browser sessions within the same
process (one indexing queue for the whole app, not one per browser tab).
"""

from __future__ import annotations

import streamlit as st

from core.background_index_builder import BackgroundIndexBuilder


@st.cache_resource
def get_shared_background_builder() -> BackgroundIndexBuilder:
    """One BackgroundIndexBuilder for the process lifetime — st.cache_resource
    (not session_state) so every browser session shares the same worker
    thread instead of each spawning its own."""
    builder = BackgroundIndexBuilder()
    builder.start()
    return builder
