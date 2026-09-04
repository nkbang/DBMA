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

from core.config import APP_VERSION, DEFAULT_GEN_MODEL, DEFAULT_TEMPERATURE, GEN_MODEL_OPTIONS
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


# 사이드바 브랜드 워드마크 "내서재"가 여는 로컬 랜딩 페이지 (Stitch 목업).
_LANDING_PAGE = (
    _PROJECT_ROOT / "docs" / "design" / "stitch" / "pastoral_research_desk" / "landing.html"
)


def _open_landing_page() -> None:
    """사이드바 "내서재" 클릭 시 로컬 랜딩 페이지를 기본 브라우저에서 연다.

    DBMA는 단일 사용자 로컬 앱이라 Streamlit 서버 프로세스와 사용자
    브라우저가 같은 기기에서 돈다 — 그래서 서버 쪽 webbrowser.open()으로
    로컬 HTML 파일을 열 수 있다. 반드시 절대경로 file:// URI로 넘겨야
    macOS URL 핸들러가 인식한다(스킴 없는 상대경로 문자열은 조용히
    무시된다 — 이전 구현이 실패한 원인).
    """
    import webbrowser

    if not _LANDING_PAGE.is_file():
        st.toast(f"랜딩 페이지를 찾을 수 없습니다: {_LANDING_PAGE}", icon="⚠️")
        return
    webbrowser.open(_LANDING_PAGE.as_uri())


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


def _render_sidebar() -> str:
    """Render the sidebar navigation.

    Returns
    -------
    str
        The selected page name.
    """
    with st.sidebar:
        # 브랜드 워드마크 "내서재 / NAE" — 클릭하면 로컬 랜딩 페이지를 연다.
        # st.button에 key를 주면 Streamlit이 감싸는 컨테이너에
        # `st-key-<key>` CSS 클래스를 붙여준다(1.58 button.py docstring에
        # 문서화된 안정 선택자). 그걸로 버튼 크롬을 걷어내 원래
        # .nae-sidebar-name 워드마크(28px/600)처럼 보이게 한다.
        if st.button("내서재", key="sidebar_brand_link", help="랜딩 페이지 열기"):
            _open_landing_page()

        st.markdown(
            f"""
            <div class="nae-sidebar-brand nae-sidebar-brand--compact">
                <div class="nae-sidebar-subtitle">NAE</div>
            </div>
            <style>
            [data-testid="stSidebar"] .st-key-sidebar_brand_link {{
                margin: 0 0 4px;
            }}
            [data-testid="stSidebar"] .st-key-sidebar_brand_link button {{
                background: transparent !important;
                border: none !important;
                box-shadow: none !important;
                min-height: 0 !important;
                padding: 0 16px !important;
                width: auto !important;
            }}
            [data-testid="stSidebar"] .st-key-sidebar_brand_link button p {{
                color: {THEME.TEXT_PRIMARY} !important;
                font-family: 'Hanken Grotesk', sans-serif !important;
                font-size: 28px !important;
                font-weight: 600 !important;
                line-height: 1.1 !important;
            }}
            [data-testid="stSidebar"] .st-key-sidebar_brand_link button:hover p {{
                color: {THEME.BRAND_PRIMARY} !important;
                text-decoration: underline;
                text-underline-offset: 4px;
            }}
            .nae-sidebar-brand--compact {{
                margin-top: 0;
            }}
            .nae-sidebar-brand--compact .nae-sidebar-subtitle {{
                margin-top: 0;
            }}
            </style>
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

        _render_settings_expander()

        st.markdown(f"""
        <div style="text-align: left; padding: 24px 16px 0;">
                <span style="font-size: 10px; color: {THEME.TEXT_TERTIARY};">
                내서재 · NAE v{APP_VERSION}
            </span>
        </div>
        """, unsafe_allow_html=True)

        return selected


# Session-state keys the answer path reads its overrides from. Kept here (not
# in core/config.py) because they are a UI-session concept — core defaults
# stay the single source of truth for anything running outside Streamlit.
SETTINGS_GEN_MODEL_KEY = "settings_gen_model"
SETTINGS_TEMPERATURE_KEY = "settings_temperature"


def _render_settings_expander() -> None:
    """Sidebar 설정 — 답변 생성에 쓰이는 모델/창의성을 세션 단위로 바꾼다.

    [docs/UI-REALIGNMENT-PROPOSAL-v1.md §P1] 이 앱에는 설정 UI가 아예
    없었다 — 설정 화면이던 ui/sidebar.py가 어디서도 import되지 않는 죽은
    코드였기 때문(2026-08-25 격리, §P2). 특히 생성 모델 선택이 없어서
    config.yaml의 default_gen_model을 바꾸는 것 외에는 방법이 없었고,
    config.yaml 주석 스스로가 "재도입하려면 GEN_MODEL_OPTIONS 기반 UI
    모델 선택이 필요"하다고 지적해둔 상태였다 — 무거운 기본 모델
    (my-theology-bot-v2, 128GB급)과 가벼운 대안(llama3.1:8b) 사이의
    선택을 사용자 기기에 맞게 넘겨주는 것이 이 위젯의 목적이다.

    범위가 이 둘뿐인 이유(조사 결과, 나머지는 이미 다른 탭에 있음):
    chunk_size/overlap/OCR은 자료 등록 탭(ui/pages/processing.py)에,
    top_k는 자료 찾기 탭 슬라이더(ui/pages/research.py)에 이미 있어
    여기 또 넣으면 중복이다. 휴지통 보관기간은 config.yaml을 읽는
    모듈 상수라 재시작 없이는 바꿔도 반영되지 않아 제외했다.

    세션 범위인 것도 의도적이다 — config.yaml에 쓰면 재시작해야 반영되고,
    git 추적 파일을 UI가 실행 중에 고쳐 쓰게 된다.
    """
    with st.expander("설정", expanded=False):
        options = list(GEN_MODEL_OPTIONS)
        if DEFAULT_GEN_MODEL not in options:
            options.insert(0, DEFAULT_GEN_MODEL)
        current = st.session_state.get(SETTINGS_GEN_MODEL_KEY, DEFAULT_GEN_MODEL)

        st.selectbox(
            "답변 생성 모델",
            options=options,
            index=options.index(current) if current in options else 0,
            key=SETTINGS_GEN_MODEL_KEY,
            help=(
                "AI 답변을 만들 때 쓰는 모델입니다. 기본 모델이 무거워 "
                "느리거나 메모리가 부족하면 더 가벼운 모델로 바꾸세요. "
                "이 창을 닫으면(앱 재시작) 기본값으로 돌아갑니다."
            ),
        )
        st.slider(
            "답변 창의성",
            min_value=0.0,
            max_value=1.0,
            value=float(st.session_state.get(SETTINGS_TEMPERATURE_KEY, DEFAULT_TEMPERATURE)),
            step=0.05,
            key=SETTINGS_TEMPERATURE_KEY,
            help=(
                "낮을수록 근거 문서에 충실하고 일관된 답변, 높을수록 "
                "표현이 자유로워집니다. 신학 자료 인용에는 낮은 값을 권합니다."
            ),
        )
        st.caption(
            "청킹·OCR 설정은 '자료 등록' 탭, 검색 결과 개수는 '자료 찾기' 탭에 있습니다."
        )


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