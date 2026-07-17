"""DBMA v1.1.0 — Personal Knowledge Operating System.

Main application entry point with navigation across all pages.
"""

from pathlib import Path
import streamlit as st
import sys

# Configure page
st.set_page_config(
    page_title="DBMA — Personal Knowledge Operating System",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

from core.config import APP_VERSION
from ui.theme.colors import THEME
from ui.pages.dashboard import render_dashboard_page
from ui.pages.library import render_library_page
from ui.pages.processing import render_processing_page
from ui.pages.research import render_research_page
from ui.pages.monitor import render_monitor_page
from ui.pages.chat import render_chat_page


def main() -> None:
    """Main application entry point."""

    # ── Global Styles ──────────────────────────────────────────
    _apply_global_styles()

    # ── Application Header ─────────────────────────────────────
    _render_app_header()

    # ── Sidebar Navigation ─────────────────────────────────────
    page = _render_sidebar()

    # ── Page Content ───────────────────────────────────────────
    _render_page_content(page)


def _apply_global_styles() -> None:
    """Apply global CSS styles."""
    st.markdown("""
        <style>
        /* Main container styling */
        .main > div {
            padding: 2rem 3rem;
        }

        /* Sidebar styling */
        .css-1egun95 {
            background-color: #fafbfc;
        }

        /* Custom component styles */
        [data-testid="stMetric"] {
            background-color: white;
            padding: 0.5rem 1rem;
            border-radius: 6px;
            border: 1px solid #e0e0e0;
        }

        /* Table styling */
        [data-testid="stDataFrame"] {
            border: 1px solid #e0e0e0;
            border-radius: 6px;
        }

        /* Footer styling */
        footer {
            visibility: hidden;
        }
        </style>
    """, unsafe_allow_html=True)


def _render_app_header() -> None:
    """Render the application header."""
    col1, col2, col3 = st.columns([1, 4, 1])

    with col1:
        logo_path = Path("DBMA_core.svg")
        if logo_path.exists():
            st.logo(str(logo_path), icon_image=str(logo_path))

    with col2:
        st.markdown(f"""
        <div style="padding: 0.5rem 0;">
            <h1 style="font-size: 24px; font-weight: 700; color: {THEME.TEXT_PRIMARY}; margin: 0;">
                DBMA
            </h1>
            <p style="font-size: 12px; color: {THEME.TEXT_SECONDARY}; margin: 0;">
                David Bang Ministry Archive — Personal Knowledge Operating System
            </p>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div style="text-align: right; padding: 0.5rem 0;">
                <span style="font-size: 11px; color: {THEME.TEXT_TERTIARY};">
                v{APP_VERSION}
            </span>
        </div>
        """, unsafe_allow_html=True)


def _render_sidebar() -> str:
    """Render the sidebar navigation.

    Returns
    -------
    str
        The selected page name.
    """
    with st.sidebar:
        st.markdown("### 📑 네비게이션")

        pages = {
            "Dashboard": ("🏠", "시스템 대시보드"),
            "Library": ("📚", "문서 라이브러리"),
            "Processing": ("📄", "문서 처리"),
            "Research": ("🔬", "연구_workspace"),
            "Chat": ("💬", "RAG 채팅"),
            "Monitor": ("💚", "시스템 모니터링"),
        }

        selected = st.radio(
            "페이지 선택",
            options=list(pages.keys()),
            label_visibility="collapsed",
        )

        st.divider()

        # System status summary
        st.markdown("### 📊 시스템 상태")
        st.caption("벡터DB: 정상")
        st.caption("임베딩: 정상")
        st.caption("파일시스템: 정상")

        st.divider()

        # Version info
        st.markdown(f"""
        <div style="text-align: center; padding: 0.5rem 0;">
                <span style="font-size: 10px; color: {THEME.TEXT_TERTIARY};">
                DBMA v{APP_VERSION}
            </span>
            <br>
            <span style="font-size: 10px; color: {THEME.TEXT_TERTIARY};">
                David Bang Ministry Archive
            </span>
        </div>
        """, unsafe_allow_html=True)

        return selected


def _render_page_content(page: str) -> None:
    """Render the selected page content.

    Parameters
    ----------
    page : str
        Selected page name.
    """
    page_renderers = {
        "Dashboard": render_dashboard_page,
        "Library": render_library_page,
        "Processing": render_processing_page,
        "Research": render_research_page,
        "Chat": render_chat_page,
        "Monitor": render_monitor_page,
    }

    renderer = page_renderers.get(page)
    if renderer:
        renderer()


if __name__ == "__main__":
    main()