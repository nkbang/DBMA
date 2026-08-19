"""내서재(NAE) 온보딩 시작 화면.

Stitch "프리미엄 랜딩 페이지" 디자인을 Streamlit으로 옮긴 첫 실행
환영 화면. 브랜드 표기는 사용자-facing이므로 "내서재"/"NAE"를 사용하고,
내부 식별자 DBMA는 그대로 유지한다
(``docs/governance/DBMA-BRAND-GOV-001.md`` 참고).
"""

import streamlit as st

_FONT_LINKS = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Hanken+Grotesk:wght@400;500;600;700;800&family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;1,8..60,400&display=swap" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet">
"""

_STYLE = """
<style>
.nae-topnav {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 4px 32px;
    border-bottom: 1px solid #e4e2dd;
    margin-bottom: 40px;
}
.nae-topnav .brand {
    font-family: 'Source Serif 4', serif;
    font-size: 20px;
    font-weight: 700;
    color: #171e1e;
}
.nae-topnav .links {
    display: flex;
    gap: 24px;
    font-family: 'Hanken Grotesk', sans-serif;
    font-size: 14px;
    color: #6a5c4c;
}
.nae-hero {
    text-align: center;
    padding: 0 24px;
}
.nae-hero .classical-title {
    font-family: 'Source Serif 4', serif;
    font-size: 52px;
    line-height: 1.1;
    font-weight: 700;
    color: #171e1e;
    margin: 0 0 6px;
}
.nae-hero .classical-subtitle {
    font-family: 'Hanken Grotesk', sans-serif;
    font-size: 22px;
    font-weight: 300;
    letter-spacing: 0.1em;
    color: #6a5c4c;
    margin: 0 0 40px;
}
.nae-hero .headline {
    font-family: 'Source Serif 4', serif;
    font-size: 30px;
    font-weight: 600;
    color: #1b1c19;
    line-height: 1.35;
    margin: 0 0 16px;
}
.nae-hero .subheadline {
    font-family: 'Hanken Grotesk', sans-serif;
    font-size: 16px;
    line-height: 1.8;
    color: #434848;
    max-width: 520px;
    margin: 0 auto 8px;
}
.nae-section-title {
    text-align: center;
    font-family: 'Hanken Grotesk', sans-serif;
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 0.05em;
    color: #6f6050;
    text-transform: uppercase;
    margin: 8px 0 20px;
}
.nae-card {
    background: #ffffff;
    border: 1px solid #c3c7c7;
    border-radius: 16px;
    padding: 32px 24px;
    text-align: center;
    height: 100%;
    box-shadow: 0 4px 24px -1px rgba(0, 0, 0, 0.03);
}
.nae-card .icon {
    width: 48px;
    height: 48px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    margin: 0 auto 20px;
    background: #f0dcc8;
}
.nae-card .icon .material-symbols-outlined {
    color: #6f6050;
    font-size: 24px;
}
.nae-card h3 {
    font-family: 'Hanken Grotesk', sans-serif;
    font-size: 18px;
    font-weight: 600;
    color: #171e1e;
    margin: 0 0 10px;
}
.nae-card p {
    font-family: 'Hanken Grotesk', sans-serif;
    font-size: 14px;
    color: #434848;
    margin: 0;
    line-height: 1.5;
}
.nae-quote {
    text-align: center;
    font-family: 'Source Serif 4', serif;
    font-style: italic;
    font-size: 19px;
    line-height: 1.6;
    color: #171e1e;
    opacity: 0.85;
    max-width: 640px;
    margin: 48px auto 8px;
}
.nae-quote .rule {
    width: 64px;
    height: 1px;
    background: #c3c7c7;
    margin: 24px auto;
}
.nae-footer {
    text-align: center;
    margin-top: 40px;
    padding-top: 24px;
    border-top: 1px solid #e4e2dd;
}
.nae-footer .tagline {
    font-family: 'Source Serif 4', serif;
    font-style: italic;
    font-size: 15px;
    color: #6a5c4c;
    margin: 0 0 4px;
}
.nae-footer .copyright {
    font-family: 'Hanken Grotesk', sans-serif;
    font-size: 12px;
    color: #737878;
    opacity: 0.7;
    margin: 0;
}
div[data-testid="stButton"] button[kind="primary"] {
    background-color: #171e1e !important;
    border-color: #171e1e !important;
    color: #ffffff !important;
    border-radius: 12px !important;
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
    border-radius: 12px !important;
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

    # ── Top Nav (장식용 — 아직 로그인/탐색 기능 없음, 프리미엄 랜딩
    # 톤만 물려받는다) ────────────────────────────────────────────
    st.markdown(
        """
        <div class="nae-topnav">
            <span class="brand">內書齋</span>
            <span class="links">서재 · 연구 · 탐색</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Hero ───────────────────────────────────────────────────
    st.markdown(
        """
        <div class="nae-hero">
            <div class="classical-title">內書齋</div>
            <div class="classical-subtitle">내서재</div>
            <div class="headline">책이 답하고,<br>기록이 말합니다.</div>
            <p class="subheadline">
                개인의 자료와 연구를 하나의 지식으로 연결하는<br>
                목회자를 위한 AI 연구실
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Hero Actions ───────────────────────────────────────────
    _, btn_col1, btn_col2, _ = st.columns([2, 1.4, 1.4, 2])
    with btn_col1:
        start_clicked = st.button(
            "연구 시작하기", use_container_width=True, type="primary"
        )
    with btn_col2:
        load_clicked = st.button("자료 불러오기", use_container_width=True)

    if start_clicked or load_clicked:
        st.session_state["show_onboarding"] = False
        st.session_state["nav_page"] = "Library"
        st.rerun()

    st.write("")
    st.write("")

    # ── Feature Cards (소개용 — 클릭 이동 없음, 랜딩 원본과 동일) ──
    st.markdown('<div class="nae-section-title">내서재가 하는 일</div>', unsafe_allow_html=True)
    cards = [
        ("auto_stories", "나의 서재", "모든 흩어진 자료를 하나의 지식 저장소로. PDF, 텍스트, 이미지 자료까지 스마트하게 관리합니다."),
        ("account_tree", "지식 연결", "문서와 설교, 개인의 메모를 의미 중심으로 연결하여 당신만의 독창적인 신학 세계를 구축합니다."),
        ("auto_awesome", "목회 연구", "말씀 연구와 설교 준비를 위한 AI 동반자. 방대한 텍스트에서 통찰을 추출하고 구조를 제안합니다."),
    ]
    cols = st.columns(3)
    for col, (icon, title, desc) in zip(cols, cards):
        with col:
            st.markdown(
                f"""
                <div class="nae-card">
                    <div class="icon"><span class="material-symbols-outlined">{icon}</span></div>
                    <h3>{title}</h3>
                    <p>{desc}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # ── Quote ──────────────────────────────────────────────────
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
    skip_clicked = st.button("나중에 하기", key="_onboard_skip")
    if skip_clicked:
        st.session_state["show_onboarding"] = False
        st.rerun()

    # ── Footer ─────────────────────────────────────────────────
    st.markdown(
        """
        <div class="nae-footer">
            <p class="tagline">"생각을 쌓고, 말씀을 잇다."</p>
            <p class="copyright">© 2026 내서재. 목회자를 위한 디지털 서재입니다.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
