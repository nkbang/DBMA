"""도움말 — 내서재(NAE) 활용 가이드.

Stitch "홈 대시보드" 화면의 도움말 카드에서 이어지는 단독 페이지.
"""

import streamlit as st

from ui.theme.colors import THEME

_FONT_LINK = """
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet">
"""

_GUIDES = [
    ("search", "자료 찾기", "성경, 책, 설교, 신학 자료를 한곳에서 검색합니다. 사이드바의 '자료 찾기'에서 시작하세요."),
    ("account_tree", "연구하기", "선택한 자료를 캔버스에 모아 AI와 함께 깊이 있는 신학 연구를 진행합니다."),
    ("auto_stories", "설교 준비", "연구 노트를 바탕으로 설교문 초안을 작성하고 다듬습니다."),
    ("folder_open", "내 자료", "저장한 자료와 진행 중인 작업을 다시 이어갈 수 있습니다."),
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
                <p style="color: {THEME.TEXT_SECONDARY}; margin: 4px 0 0;">내서재를 더 잘 활용하는 방법을 안내합니다.</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    cols = st.columns(2)
    for i, (icon, title, desc) in enumerate(_GUIDES):
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

    st.divider()
    st.caption("추가 문의사항은 관리자에게 문의하세요.")
