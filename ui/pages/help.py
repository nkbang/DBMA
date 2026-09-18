"""도움말 — 내서재(NAE) 활용 가이드.

Stitch "도움말" 화면의 보이는 흐름을 실제 Streamlit 앱에 맞춰 재현한다.
"""

import streamlit as st

from core.self_diagnostic import run_self_diagnostic
from ui.theme.colors import THEME

_STATUS_ICON = {"정상": "check_circle", "확인 필요": "info", "오류": "error"}

_FONT_LINK = """
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet">
"""

_GUIDES = [
    (
        "intro",
        "search",
        "내서재는 무엇인가?",
        "목회자의 연구와 설교를 돕는 신학 지원 시스템입니다.",
        "내서재는 자료 보관, 검색, 연구, 설교 준비를 한 흐름으로 연결해 주는 신학 연구실입니다. 각 기능은 서로 연결되어 있어, 자료를 찾고 보관하며 AI와 함께 정리하는 과정이 자연스럽게 이어집니다.",
    ),
    (
        "guide_search",
        "search",
        "자료 찾는 방법",
        "성경, 책, 설교, 신학 자료를 한 곳에서 검색하세요.",
        "검색어를 입력하고 자료 유형을 선택하면 관련 자료를 빠르게 확인할 수 있습니다. 필요한 자료를 찾고 나면, 바로 연구 세션에서 연결해 사용할 수 있습니다.",
    ),
    (
        "guide_research",
        "account_tree",
        "연구하는 방법",
        "자료를 찾고 → 중요한 내용을 모으고 → 연구합니다.",
        "검색 결과에서 핵심 자료를 선택해 함께 모아두고, 메모와 질문을 남기며 깊이 있는 연구를 이어가세요. 이 과정은 설교 준비와도 자연스럽게 연결됩니다.",
    ),
    (
        "guide_sermon",
        "auto_stories",
        "설교 준비하는 방법",
        "연구한 자료를 설교 준비로 자연스럽게 이어갑니다.",
        "연구를 바탕으로 본문과 주제를 정리하고, 초안을 작성한 뒤 수정·검토해 최종 설교문으로 다듬어갑니다. 준비된 자료와 메모가 설교문 작성 화면으로 이어집니다.",
    ),
]

_EXAMPLES = [
    (
        "example_research",
        "auto_stories",
        "로마서 8장 연구 예제",
        "완성된 연구 workflow를 확인해보세요.",
        "로마서 8장에 대한 연구 질문을 입력하고, 관련 자료를 찾은 뒤 메모와 참고문헌을 정리하는 흐름을 살펴볼 수 있습니다.",
    ),
    (
        "example_sermon",
        "menu_book",
        "설교 준비 예제",
        "연구에서 설교까지 이어지는 흐름입니다.",
        "연구한 자료를 설교 준비 화면으로 옮겨 본문과 주제를 정리하고, 초안을 작성해 본문 구성까지 자연스럽게 이어가는 예시를 확인할 수 있습니다.",
    ),
]


def render_help_page() -> None:
    """도움말 페이지를 렌더링한다."""
    st.markdown(_FONT_LINK, unsafe_allow_html=True)

    st.markdown(
        f"""
        <div style="padding: 0.5rem 0 1.5rem; display: flex; align-items: center; gap: 10px;">
            <span class="material-symbols-outlined" style="color: {THEME.BRAND_PRIMARY}; font-size: 28px;">help</span>
            <div>
                <h2 style="color: {THEME.TEXT_PRIMARY}; margin: 0;">도움말</h2>
                <p style="color: {THEME.TEXT_SECONDARY}; margin: 4px 0 0;">처음 시작하는 분들을 위한 안내입니다.</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"<h3 style=\"margin: 0 0 1rem; color: {THEME.TEXT_SECONDARY}; font-size: 20px;\">처음 시작하는 분들을 위해</h3>",
        unsafe_allow_html=True,
    )

    cols = st.columns(2)
    open_guide = st.session_state.get("help_open_guide")
    for i, (_, icon, title, desc, detail) in enumerate(_GUIDES):
        with cols[i % 2]:
            st.markdown(
                f"""
                <div style="
                    background: {THEME.BG_SURFACE};
                    border: 1px solid {THEME.BORDER_LIGHT};
                    border-radius: 12px;
                    padding: 24px;
                    margin-bottom: 16px;
                    box-shadow: 0 4px 24px -1px rgba(0, 0, 0, 0.03);
                ">
                    <div style="
                        width: 44px; height: 44px; border-radius: 10px;
                        background: {THEME.BG_PAGE};
                        display: flex; align-items: center; justify-content: center;
                        margin-bottom: 14px;
                    ">
                        <span class="material-symbols-outlined" style="color: {THEME.BRAND_SECONDARY}; font-size: 22px;">{icon}</span>
                    </div>
                    <div style="font-weight: 600; color: {THEME.TEXT_PRIMARY}; margin-bottom: 6px;">{title}</div>
                    <div style="font-size: 13px; color: {THEME.TEXT_SECONDARY};">{desc}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            key = f"help_guide_{_GUIDES[i][0]}"
            if st.button("닫기" if open_guide == _GUIDES[i][0] else "보기", key=key, use_container_width=True):
                st.session_state["help_open_guide"] = None if open_guide == _GUIDES[i][0] else _GUIDES[i][0]
                st.rerun()
            if open_guide == _GUIDES[i][0]:
                st.info(detail)

    st.markdown(
        f"<h3 style=\"margin: 2rem 0 1rem; color: {THEME.TEXT_SECONDARY}; font-size: 20px;\">실제 예제 보기</h3>",
        unsafe_allow_html=True,
    )

    for _, icon, title, desc, detail in _EXAMPLES:
        st.markdown(
            f"""
            <div style="
                display: flex; align-items: center; justify-content: space-between; gap: 16px;
                background: {THEME.BG_SURFACE};
                border: 1px solid {THEME.BORDER_LIGHT};
                border-radius: 12px;
                padding: 20px 24px;
                margin-bottom: 12px;
            ">
                <div style="display: flex; align-items: center; gap: 14px;">
                    <span class="material-symbols-outlined" style="color: {THEME.BRAND_SECONDARY}; font-size: 28px;">{icon}</span>
                    <div>
                        <div style="font-size: 18px; font-weight: 700; color: {THEME.TEXT_PRIMARY}; margin-bottom: 4px;">{title}</div>
                        <div style="font-size: 13px; color: {THEME.TEXT_SECONDARY};">{desc}</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("예제 보기", key=f"help_example_{_EXAMPLES[0][0] if title == _EXAMPLES[0][2] else _EXAMPLES[1][0]}", use_container_width=False):
            st.session_state["help_example_open"] = title
            st.info(detail)

    _render_self_diagnostic_section()

    st.caption(
        "이 앱은 별도 유료 지원이 제공되지 않습니다(as-is). "
        "문제가 있으면 위 자가 진단 결과를 확인한 뒤, 그래도 해결되지 않으면 "
        "관리자에게 문의해 주세요."
    )


def _render_self_diagnostic_section() -> None:
    """[S5-3] 자가 진단 — 사용자가 스스로 눌러 앱 상태를 확인할 수 있게
    한다. David에게 로그를 보내지 않고도 "무엇이 문제인지"를 먼저
    좁힐 수 있도록 하는 1차 방어선이다."""
    st.markdown(
        f"<h3 style=\"margin: 2rem 0 1rem; color: {THEME.TEXT_SECONDARY}; font-size: 20px;\">앱 상태 자가 진단</h3>",
        unsafe_allow_html=True,
    )
    st.caption("문제가 있어 보일 때 눌러보세요 — Ollama 연결, 필수 모델, 디스크 여유, 성경 본문, 자료 건수를 확인합니다.")

    if st.button("자가 진단 실행", key="help_run_self_diagnostic", icon=":material/health_and_safety:"):
        with st.spinner("확인하는 중..."):
            st.session_state["help_diagnostic_results"] = run_self_diagnostic()

    results = st.session_state.get("help_diagnostic_results")
    if not results:
        return

    for r in results:
        icon = _STATUS_ICON.get(r.status, "help")
        if r.status == "정상":
            bg, fg = THEME.STATUS_SUCCESS_BG, THEME.STATUS_SUCCESS
        elif r.status == "확인 필요":
            bg, fg = THEME.STATUS_WARNING_BG, THEME.STATUS_WARNING
        else:
            bg, fg = THEME.STATUS_ERROR_BG, THEME.STATUS_ERROR
        st.markdown(
            f"""
            <div style="
                display: flex; align-items: flex-start; gap: 10px;
                background: {bg}; border-radius: 8px; padding: 12px 16px; margin-bottom: 8px;
            ">
                <span class="material-symbols-outlined" style="color: {fg}; font-size: 20px;">{icon}</span>
                <div>
                    <div style="font-weight: 600; color: {THEME.TEXT_PRIMARY}; font-size: 14px;">{r.title} — {r.status}</div>
                    <div style="font-size: 13px; color: {THEME.TEXT_SECONDARY};">{r.detail}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
