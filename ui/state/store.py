"""DBMA Design System — Centralized Session State Store.

Provides a unified interface for managing all Streamlit session state
keys used across DBMA pages and components, preventing ad-hoc access.
"""

from typing import Any, Optional


class StateStore:
    """Centralized session state store for DBMA UI.

    All page and component state should flow through this class
    to ensure consistency and prevent key collisions.

    Usage
    -----
        store = StateStore()
        store.set("processing_target", "/data/raw")
        value = store.get("processing_target", "/default")
    """

    # ── Namespaced key prefixes ──────────────────────────────
    _PREFIXES = {
        "app": "dbma_app",
        "sidebar": "dbma_sidebar",
        "processing": "dbma_processing",
        "library": "dbma_library",
        "research": "dbma_research",
        "dashboard": "dbma_dashboard",
        "monitor": "dbma_monitor",
    }

    def __init__(self):
        """Initialize the state store and sync with Streamlit."""
        import streamlit as st
        self._store = st.session_state  # type: ignore[name-defined]

    def get(self, key: str, default: Any = None) -> Any:
        """Get a session state value.

        Parameters
        ----------
        key : str
            State key name.
        default : Any
            Default value if key not set.

        Returns
        -------
        Any
            Stored value or default.
        """
        full_key = f"{self._PREFIXES.get(key.split('_')[0], 'dbma')}_{key}"
        return self._store.get(full_key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a session state value.

        Parameters
        ----------
        key : str
            State key name.
        value : Any
            Value to store.
        """
        parts = key.split("_")
        prefix = self._PREFIXES.get(parts[0], "dbma") if parts else "dbma"
        full_key = f"{prefix}_{key}"
        self._store[full_key] = value

    def has(self, key: str) -> bool:
        """Check if a state key exists.

        Parameters
        ----------
        key : str
            State key name.

        Returns
        -------
        bool
            True if the key exists in session state.
        """
        parts = key.split("_")
        prefix = self._PREFIXES.get(parts[0], "dbma") if parts else "dbma"
        full_key = f"{prefix}_{key}"
        return full_key in self._store

    def delete(self, key: str) -> bool:
        """Delete a session state key.

        Parameters
        ----------
        key : str
            State key name.

        Returns
        -------
        bool
            True if the key was deleted, False if it didn't exist.
        """
        parts = key.split("_")
        prefix = self._PREFIXES.get(parts[0], "dbma") if parts else "dbma"
        full_key = f"{prefix}_{key}"
        if full_key in self._store:
            del self._store[full_key]
            return True
        return False

    def clear_namespace(self, namespace: str) -> int:
        """Clear all keys in a namespace.

        Parameters
        ----------
        namespace : str
            Namespace prefix to clear (e.g., 'processing').

        Returns
        -------
        int
            Number of keys cleared.
        """
        prefix = f"{self._PREFIXES.get(namespace, 'dbma')}_"
        keys_to_delete = [k for k in self._store if k.startswith(prefix)]
        for k in keys_to_delete:
            del self._store[k]
        return len(keys_to_delete)

    @property
    def all(self) -> dict:
        """Return all session state as a dict (for debugging)."""
        return dict(self._store)


# Predefined state key constants for common values
PROCESSING_TARGET = "processing_target"
PROCESSING_OUTPUT = "processing_output"
PROCESSING_CHUNK_SIZE = "chunk_size"
PROCESSING_CHUNK_OVERLAP = "chunk_overlap"
PROCESSING_USE_OCR = "use_ocr"
LIBRARY_VIEW_MODE = "library_view_mode"
LIBRARY_SEARCH_QUERY = "library_search_query"
LIBRARY_SELECTED_DOC = "library_selected_doc"
LIBRARY_PAGE = "library_page"
RESEARCH_QUERY = "research_query"
RESEARCH_TOP_K = "research_top_k"
DASHBOARD_AUTO_REFRESH = "dashboard_auto_refresh"
MONITOR_PAGE = "monitor_page"