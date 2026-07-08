"""DBMA Design System — State management package.

Centralized session state store to prevent ad-hoc st.session_state usage
across pages and components.
"""

from ui.state.store import StateStore

__all__ = ["StateStore"]