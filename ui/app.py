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
from ui.pages.chat import render_chat_page
from ui.pages.monitor import render_monitor_page
from ui.pages.sermon_draft import render_sermon_draft_page
from ui.pages.sermon_research import render_sermon_research_hub_page
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

    # ── Sidebar Navigation ─────────────────────────────────────
    page = _render_sidebar()

    # ── Page Content ───────────────────────────────────────────
    _render_page_content(page)


def _apply_global_styles() -> None:
    """Apply global CSS styles."""
    st.markdown(f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Hanken+Grotesk:wght@400;500;600;700&family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600&display=swap');
        @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap');

        .material-symbols-outlined {{
            font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24;
            vertical-align: middle;
        }}

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
            min-width: 280px;
            max-width: 280px;
        }}
        [data-testid="stSidebar"] > div:first-child {{
            padding: 48px 16px 24px;
        }}
        .nae-sidebar-brand {{
            margin: 0 16px 32px;
        }}
        .nae-sidebar-name {{
            color: {THEME.TEXT_PRIMARY};
            font-family: 'Hanken Grotesk', sans-serif;
            font-size: 28px;
            font-weight: 600;
            line-height: 1.1;
        }}
        .nae-sidebar-subtitle {{
            color: {THEME.TEXT_SECONDARY};
            font-family: 'Hanken Grotesk', sans-serif;
            font-size: 14px;
            margin-top: 4px;
        }}
        [data-testid="stSidebar"] h3 {{
            color: {THEME.TEXT_PRIMARY};
            font-family: 'Hanken Grotesk', sans-serif;
            font-size: 20px;
            margin: 0 16px 24px;
        }}
        [data-testid="stSidebar"] [data-testid="stRadio"] label {{
            border-radius: 4px;
            color: {THEME.TEXT_SECONDARY};
            font-family: 'Hanken Grotesk', sans-serif;
            font-size: 14px;
            padding: 8px 12px;
        }}
        [data-testid="stSidebar"] [data-testid="stRadio"] label:hover {{
            background: {THEME.BG_PAGE};
            color: {THEME.TEXT_PRIMARY};
        }}
        .nae-page-header {{
            align-items: center;
            border-bottom: 1px solid {THEME.BORDER_MEDIUM};
            display: flex;
            justify-content: space-between;
            margin: -32px -48px 32px;
            min-height: 64px;
            padding: 0 32px;
        }}
        .nae-page-title {{
            color: {THEME.TEXT_PRIMARY};
            font-family: 'Hanken Grotesk', sans-serif;
            font-size: 20px;
            font-weight: 600;
        }}
        .nae-page-meta {{
            color: {THEME.TEXT_TERTIARY};
            font-family: 'Hanken Grotesk', sans-serif;
            font-size: 12px;
        }}
        .nae-section-heading {{
            border-bottom: 1px solid {THEME.BORDER_LIGHT};
            color: {THEME.TEXT_PRIMARY};
            font-family: 'Hanken Grotesk', sans-serif;
            font-size: 20px;
            font-weight: 600;
            margin: 32px 0 16px;
            padding-bottom: 8px;
        }}
        .nae-fixed-footer {{
            align-items: center;
            background: {THEME.BRAND_PRIMARY};
            bottom: 0;
            color: {THEME.TEXT_INVERSE};
            display: flex;
            font-family: 'Hanken Grotesk', sans-serif;
            font-size: 12px;
            justify-content: space-between;
            left: 280px;
            min-height: 40px;
            padding: 0 32px;
            position: fixed;
            right: 0;
            z-index: 100;
        }}
        .nae-footer-link {{
            color: #c2e8fe;
        }}
        [data-testid="stHeader"] {{
            background-color: transparent;
        }}

        /* Main container styling */
        .main > div {{
            padding: 48px;
            padding-bottom: 72px;
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
        body > footer {{
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
        st.markdown(
            """
            <div class="nae-sidebar-brand">
                <div class="nae-sidebar-name">내서재</div>
                <div class="nae-sidebar-subtitle">NAE</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        pages = {
            "Dashboard": "홈",
            "Library": "내 자료",
            "Processing": "자료 등록",
            "Research": "자료 찾기",
            "AI에게 질문": "AI에게 질문",
            "설교 연구": "연구하기",
            "설교문 작성": "설교 준비",
            "설교 리뷰": "설교 모음 정리",
        }
        # [NAE-UPLOAD-AUTO] 자료 등록(업로드) 화면은 일반 사용자도 직접
        # 자료를 올릴 수 있어야 해서 항상 노출한다 — 이전에는 "일반
        # 사용자에게 불필요"하다는 가정으로 NAE_ADMIN_MODE 뒤에 숨겨져
        # 있었으나, 그러면 베타 테스터는 UI로 문서를 업로드할 방법이
        # 아예 없었다(사용자 보고, 2026-08-23). 엔지니어링 내부 진단
        # 화면(시스템 모니터링)만 계속 NAE_ADMIN_MODE=1일 때만 노출한다.
        if os.environ.get("NAE_ADMIN_MODE") == "1":
            pages["Monitor"] = "시스템 모니터링"
        pages["도움말"] = "도움말"

        # key="nav_page" lets other pages switch tabs programmatically
        # (e.g. Dashboard's quick-action buttons) by setting
        # st.session_state["nav_page"] before rerunning — the radio picks
        # up that value on the next render instead of needing a widget
        # reference passed around.
        selected = st.radio(
            "페이지 선택",
            options=list(pages.keys()),
            format_func=lambda key: pages[key],
            label_visibility="collapsed",
            key="nav_page",
        )

        st.markdown(f"""
        <div style="text-align: left; padding: 24px 16px 0;">
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
        "AI에게 질문": render_chat_page,
        "설교 연구": render_sermon_research_hub_page,
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