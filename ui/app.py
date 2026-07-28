"""DBMA v1.1.0 — Personal Knowledge Operating System.

Main application entry point with navigation across all pages.
"""

from pathlib import Path
import streamlit as st
import sys
import os

# Ensure project root is on sys.path so `core.*` imports work
# regardless of how/where streamlit is launched from.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# Configure page
st.set_page_config(
    page_title="내서재 · NAE",
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
from ui.pages.sermon_draft import render_sermon_draft_page
from ui.pages.sermon_review import render_sermon_review_page
from ui.pages.onboarding import render_onboarding_page
from ui.pages.help import render_help_page


def main() -> None:
    """Main application entry point."""

    # ── Global Styles ──────────────────────────────────────────
    _apply_global_styles()

    # ── First-run Onboarding ───────────────────────────────────
    if st.session_state.get("show_onboarding", True):
        render_onboarding_page()
        return

    # ── Application Header ─────────────────────────────────────
    _render_app_header()

    # ── Sidebar Navigation ─────────────────────────────────────
    page = _render_sidebar()

    # ── Page Content ───────────────────────────────────────────
    _render_page_content(page)


def _apply_global_styles() -> None:
    """Apply global CSS styles."""
    st.markdown(f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Hanken+Grotesk:wght@400;500;600;700&family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600&display=swap');

        /* Stitch Scholar design system typography */
        html, body, [class*="css"] {{
            font-family: 'Hanken Grotesk', sans-serif;
        }}

        /* App / sidebar surface colors */
        [data-testid="stAppViewContainer"] {{
            background-color: {THEME.BG_PAGE};
        }}
        [data-testid="stSidebar"] {{
            background-color: {THEME.BG_SIDEBAR};
            border-right: 1px solid {THEME.BORDER_LIGHT};
        }}
        [data-testid="stHeader"] {{
            background-color: transparent;
        }}

        /* Main container styling */
        .main > div {{
            padding: 2rem 3rem;
        }}

        /* Custom component styles */
        [data-testid="stMetric"] {{
            background-color: white;
            padding: 0.5rem 1rem;
            border-radius: 6px;
            border: 1px solid #e0e0e0;
        }}

        /* Table styling */
        [data-testid="stDataFrame"] {{
            border: 1px solid #e0e0e0;
            border-radius: 6px;
        }}

        /* Primary action buttons — Scholar Blue per DESIGN.md
           (kind is "primary" for st.button, "primaryFormSubmit" for
           st.form_submit_button — match both with a substring selector) */
        button[kind*="primary"] {{
            background-color: #171e1e !important;
            border-color: #171e1e !important;
            color: #ffffff !important;
            border-radius: 999px !important;
        }}
        button[kind*="primary"]:hover {{
            background-color: #434848 !important;
            border-color: #434848 !important;
            color: #ffffff !important;
        }}
        button[kind*="primary"] p {{
            color: #ffffff !important;
        }}
        button[kind*="secondary"] {{
            border-radius: 999px !important;
        }}

        /* Footer styling */
        footer {{
            visibility: hidden;
        }}
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
        # 사용자-facing 브랜드는 내서재/NAE — DBMA는 내부 식별자로만 유지
        # (docs/governance/DBMA-BRAND-GOV-001.md 참고)
        st.markdown(f"""
        <div style="padding: 0.5rem 0;">
            <h1 style="font-family: 'Hanken Grotesk', sans-serif; font-size: 24px; font-weight: 700; color: {THEME.TEXT_PRIMARY}; margin: 0; letter-spacing: -0.01em;">
                내서재 <span style="font-weight: 500; color: {THEME.TEXT_TERTIARY};">· NAE</span>
            </h1>
            <p style="font-family: 'Hanken Grotesk', sans-serif; font-size: 12px; color: {THEME.TEXT_SECONDARY}; margin: 0;">
                나의 자료 · 나의 연구 · 나의 목회
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
            "Dashboard": ("🏠", "홈"),
            "Library": ("🔍", "자료 찾기 · 내 자료"),
            "Processing": ("📄", "문서 처리"),
            "Research": ("🧪", "연구하기 워크스페이스"),
            "Chat": ("💬", "RAG 채팅"),
            "설교문 작성": ("📖", "설교 준비"),
            "설교 리뷰": ("🗂️", "설교 모음 분리·검수"),
            "Monitor": ("💚", "시스템 모니터링"),
            "도움말": ("❓", "내서재 활용 가이드"),
        }

        # key="nav_page" lets other pages switch tabs programmatically
        # (e.g. Dashboard's quick-action buttons) by setting
        # st.session_state["nav_page"] before rerunning — the radio picks
        # up that value on the next render instead of needing a widget
        # reference passed around.
        selected = st.radio(
            "페이지 선택",
            options=list(pages.keys()),
            label_visibility="collapsed",
            key="nav_page",
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
                내서재 · NAE v{APP_VERSION}
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
        "설교문 작성": render_sermon_draft_page,
        "설교 리뷰": render_sermon_review_page,
        "Monitor": render_monitor_page,
        "도움말": render_help_page,
    }

    renderer = page_renderers.get(page)
    if renderer:
        renderer()


if __name__ == "__main__":
    main()