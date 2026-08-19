"""내서재(NAE) 온보딩 시작 화면.

Stitch 디자인(``docs/design/stitch/pastoral_research_desk``, "온보딩: 시작하기")을
Streamlit으로 옮긴 첫 실행 환영 화면. 브랜드 표기는 사용자-facing이므로
"내서재"/"NAE"를 사용하고, 내부 식별자 DBMA는 그대로 유지한다
(``docs/governance/DBMA-BRAND-GOV-001.md`` 참고).
"""

import streamlit as st

_FONT_LINKS = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Hanken+Grotesk:wght@400;500;600;700&family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600&display=swap" rel="stylesheet">
"""

_STYLE = """
<style>
.nae-onboard {
    font-family: 'Hanken Grotesk', sans-serif;
    background: #fbf9f4;
    border: 1px solid #e4e2dd;
    border-radius: 8px;
    padding: 64px 48px 48px;
    text-align: center;
    margin-bottom: 24px;
}
.nae-onboard h1 {
    font-family: 'Hanken Grotesk', sans-serif;
    font-size: 40px;
    font-weight: 700;
    letter-spacing: -0.02em;
    color: #171e1e;
    margin: 0 0 16px;
}
.nae-onboard p.lead {
    font-family: 'Source Serif 4', serif;
    font-size: 19px;
    color: #434848;
    max-width: 560px;
    margin: 0 auto;
}
.nae-onboard p.lead b { color: #171e1e; }
.nae-card {
    background: #fbf9f4;
    border: 1px solid #c3c7c7;
    border-radius: 8px;
    padding: 32px 24px;
    text-align: center;
    height: 100%;
}
.nae-card .icon {
    width: 48px;
    height: 48px;
    border-radius: 999px;
    display: flex;
    align-items: center;
    justify-content: center;
    margin: 0 auto 20px;
    font-size: 22px;
}
.nae-card h3 {
    font-family: 'Hanken Grotesk', sans-serif;
    font-size: 20px;
    font-weight: 600;
    color: #171e1e;
    margin: 0 0 10px;
}
.nae-card p {
    font-family: 'Hanken Grotesk', sans-serif;
    font-size: 14px;
    color: #434848;
    margin: 0;
}
.nae-footer {
    text-align: center;
    font-family: 'Hanken Grotesk', sans-serif;
    font-size: 12px;
    color: #737878;
    opacity: 0.7;
    margin-top: 8px;
}
.nae-quote {
    text-align: center;
    font-family: 'Source Serif 4', serif;
    font-style: italic;
    font-size: 20px;
    line-height: 1.6;
    color: #171e1e;
    opacity: 0.85;
    max-width: 640px;
    margin: 32px auto 8px;
}
.nae-quote .rule {
    width: 64px;
    height: 1px;
    background: #c3c7c7;
    margin: 24px auto;
}
div[data-testid="stButton"] button[kind="primary"] {
    background-color: #171e1e !important;
    border-color: #171e1e !important;
    color: #ffffff !important;
    border-radius: 999px !important;
}
div[data-testid="stButton"] button[kind="primary"]:hover {
    background-color: #434848 !important;
    border-color: #434848 !important;
    color: #ffffff !important;
}
div[data-testid="stButton"] button[kind="primary"] p {
    color: #ffffff !important;
}
div[data-testid="stButton"] button[kind="secondary"] {
    background-color: transparent !important;
    border-color: #737878 !important;
    color: #1b1c19 !important;
    border-radius: 999px !important;
}
div[data-testid="stButton"] button[kind="secondary"]:hover {
    background-color: #f0eee9 !important;
    border-color: #737878 !important;
    color: #1b1c19 !important;
}
</style>
"""


def render_onboarding_page() -> None:
    """첫 실행 환영/온보딩 화면을 렌더링한다."""
    st.markdown(_FONT_LINKS + _STYLE, unsafe_allow_html=True)

    st.markdown(
        """
        <div class="nae-onboard">
            <h1>내서재에 오신 것을 환영합니다</h1>
            <p class="lead">목회자의 연구와 설교를 돕는 디지털 서재, <b>내서재</b>를 시작해보세요.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    cards = [
        ("🔍", "#dde4e3", "자료 찾기", "방대한 성경과 신학 자료를 한곳에서 검색하세요."),
        ("🧪", "#c2e8fe", "AI 연구 도우미", "맥락을 이해하는 AI와 함께 깊이 있는 신학 연구를 수행하세요."),
        ("📖", "#f3dfcb", "설교 준비", "연구 결과를 바탕으로 자연스럽게 설교문을 작성하세요."),
    ]
    cols = st.columns(3)
    for col, (icon, bg, title, desc) in zip(cols, cards):
        with col:
            st.markdown(
                f"""
                <div class="nae-card">
                    <div class="icon" style="background:{bg};">{icon}</div>
                    <h3>{title}</h3>
                    <p>{desc}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown(
        """
        <div class="nae-quote">
            <div class="rule"></div>
            "책을 읽는 것은 대화하는 것이다. 지혜의 거장들과 대화하며
            나의 신학을 세워가는 이 거룩한 노동을 돕습니다."
            <div class="rule"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.write("")
    btn_col1, btn_col2, btn_col3 = st.columns([2, 1, 1])
    with btn_col2:
        start_clicked = st.button(
            "바로 시작하기", use_container_width=True, type="primary"
        )
    with btn_col3:
        skip_clicked = st.button("나중에 하기", use_container_width=True)

    if start_clicked:
        st.session_state["show_onboarding"] = False
        st.session_state["nav_page"] = "Library"
        st.rerun()

    if skip_clicked:
        st.session_state["show_onboarding"] = False
        st.rerun()

    st.markdown(
        '<p class="nae-footer">© 2026 내서재. 목회자를 위한 디지털 서재입니다.</p>',
        unsafe_allow_html=True,
    )
