"""내서재(NAE) 온보딩 시작 화면.

Stitch "프리미엄 랜딩 페이지" 디자인을 Streamlit으로 옮긴 첫 실행
환영 화면. 브랜드 표기는 사용자-facing이므로 "내서재"/"NAE"를 사용하고,
내부 식별자 DBMA는 그대로 유지한다
(`docs/governance/DBMA-BRAND-GOV-001.md` 참고).
"""

import streamlit as st

_FONT_LINKS = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Hanken+Grotesk:wght@400;500;600;700;800&family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;1,8..60,400&display=swap" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet">
"""

_STYLE = """
<style>
/* ── 전역 배경 (따뜻한 아이보리) ─────────────────────────── */
.stApp {
    background-color: #F8F6F2;
}
main > .stMarkdown {
    padding-top: 0 !important;
}

/* ── Top Nav ─────────────────────────────────────────────── */
.nae-topnav {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px 48px;
    border-bottom: 1px solid #e4e2dd;
    background: #fbf9f4;
    position: sticky;
    top: 0;
    z-index: 50;
}
.nae-topnav .brand {
    font-family: 'Source Serif 4', serif;
    font-size: 28px;
    font-weight: 700;
    color: #171e1e;
}
.st-key-topnav_library button,
.st-key-topnav_research button,
.st-key-topnav_explore button {
    color: #6a5c4c !important;
    font-family: 'Hanken Grotesk', sans-serif !important;
    font-size: 14px !important;
    font-weight: 500 !important;
}
.st-key-topnav_library button:hover,
.st-key-topnav_research button:hover,
.st-key-topnav_explore button:hover {
    color: #171e1e !important;
}
.st-key-topnav_login button {
    color: #c3c7c7 !important;
    cursor: not-allowed !important;
    font-family: 'Hanken Grotesk', sans-serif !important;
    font-size: 14px !important;
    font-weight: 500 !important;
}

/* ── Hero ────────────────────────────────────────────────── */
.nae-hero {
    text-align: center;
    padding: 96px 24px 64px;
    max-width: 1280px;
    margin: 0 auto;
}
.nae-hero .classical-title {
    font-family: 'Source Serif 4', serif;
    font-size: 60px;
    line-height: 1.1;
    font-weight: 700;
    color: #171e1e;
    margin: 0 0 8px;
}
.nae-hero .classical-subtitle {
    font-family: 'Hanken Grotesk', sans-serif;
    font-size: 30px;
    font-weight: 300;
    letter-spacing: 0.1em;
    color: #6a5c4c;
    margin: 0 0 48px;
}
.nae-hero .headline {
    text-align: center;
    font-family: 'Source Serif 4', serif;
    font-size: 36px;
    font-weight: 600;
    color: #1b1c19;
    line-height: 1.35;
    margin: 0 0 24px;
    max-width: 672px;
}
.nae-hero .subheadline {
    font-family: 'Hanken Grotesk', sans-serif;
    font-size: 18px;
    line-height: 1.8;
    color: #434848;
    max-width: 448px;
    margin: 0 auto 80px;
}

/* ── Hero Illustration (CSS-only premium art) ───────────── */
.nae-hero-illustration {
    width: 100%;
    max-width: 896px;
    aspect-ratio: 16/9;
    overflow: hidden;
    border-radius: 16px;
    box-shadow: 0 4px 24px -1px rgba(0, 0, 0, 0.03);
    border: 1px solid #c3c7c7;
    background: linear-gradient(135deg, #f5f3ee 0%, #e8e4dc 30%, #d6c3b0 60%, #f0dcc8 100%);
    margin: 0 auto;
    position: relative;
}
.nae-hero-illustration .illust-bg {
    position: absolute;
    inset: 0;
    background:
        radial-gradient(ellipse 600px 400px at 30% 50%, rgba(106,92,76,0.12) 0%, transparent 70%),
        radial-gradient(ellipse 400px 300px at 70% 40%, rgba(26,30,30,0.08) 0%, transparent 60%),
        radial-gradient(ellipse 200px 200px at 50% 70%, rgba(12,54,71,0.06) 0%, transparent 50%);
}
.nae-hero-illustration .illust-lines {
    position: absolute;
    inset: 0;
    opacity: 0.15;
}
.nae-hero-illustration .illust-lines::before,
.nae-hero-illustration .illust-lines::after {
    content: '';
    position: absolute;
    background: #171e1e;
}
.nae-hero-illustration .illust-lines::before {
    width: 60%;
    height: 1px;
    top: 35%;
    left: 20%;
    transform: rotate(-2deg);
}
.nae-hero-illustration .illust-lines::after {
    width: 40%;
    height: 1px;
    top: 55%;
    right: 20%;
    transform: rotate(1deg);
}
.nae-hero-illustration .illust-circle {
    position: absolute;
    border-radius: 50%;
    border: 1px solid rgba(23,30,30,0.1);
}
.nae-hero-illustration .illust-circle:nth-child(1) {
    width: 120px;
    height: 120px;
    top: 20%;
    left: 25%;
}
.nae-hero-illustration .illust-circle:nth-child(2) {
    width: 80px;
    height: 80px;
    top: 45%;
    right: 30%;
}
.nae-hero-illustration .illust-circle:nth-child(3) {
    width: 60px;
    height: 60px;
    bottom: 25%;
    left: 45%;
}
.nae-hero-illustration .illust-dots {
    position: absolute;
    inset: 0;
}
.nae-hero-illustration .illust-dot {
    position: absolute;
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: rgba(23,30,30,0.15);
}
.nae-hero-illustration .illust-dot:nth-child(1) { top: 30%; left: 35%; }
.nae-hero-illustration .illust-dot:nth-child(2) { top: 60%; right: 35%; }
.nae-hero-illustration .illust-dot:nth-child(3) { bottom: 35%; left: 55%; }
.nae-hero-illustration .overlay {
    position: absolute;
    inset: 0;
    background: linear-gradient(to top, rgba(248,246,242,0.15), transparent);
    pointer-events: none;
}

/* ── Feature Cards ───────────────────────────────────────── */
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
.nae-features-section {
    padding: 96px 48px;
    background: #f5f3ee;
    border-top: 1px solid #c3c7c7;
    border-bottom: 1px solid #c3c7c7;
}
.nae-card {
    background: #ffffff;
    border: 1px solid #c3c7c7;
    border-radius: 16px;
    padding: 40px 24px;
    text-align: center;
    height: 100%;
    box-shadow: 0 4px 24px -1px rgba(0, 0, 0, 0.03);
    transition: border-color 0.3s;
}
.nae-card:hover {
    border-color: #171e1e;
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
    font-size: 20px;
    font-weight: 600;
    color: #171e1e;
    margin: 0 0 16px;
}
.nae-card p {
    font-family: 'Source Serif 4', serif;
    font-size: 17px;
    color: #434848;
    margin: 0;
    line-height: 1.65;
}

/* ── Quote ───────────────────────────────────────────────── */
.nae-quote-section {
    padding: 128px 48px;
    max-width: 720px;
    margin: 0 auto;
    text-align: center;
}
.nae-quote .rule {
    width: 64px;
    height: 1px;
    background: #c3c7c7;
    margin: 40px auto;
}
.nae-quote blockquote {
    word-break: keep-all;
    overflow-wrap: normal;
    font-family: 'Source Serif 4', serif;
    font-style: italic;
    font-size: 28px;
    line-height: 1.6;
    color: #171e1e;
    opacity: 0.85;
    margin: 0;
}

/* ── Footer ──────────────────────────────────────────────── */
.nae-footer {
    padding: 48px;
    background: #f0eee9;
    border-top: 1px solid #c3c7c7;
}
.nae-footer .footer-inner {
    max-width: 1280px;
    margin: 0 auto;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 48px;
}
@media (min-width: 768px) {
    .nae-footer .footer-inner {
        flex-direction: row;
        justify-content: space-between;
    }
}
.nae-footer .brand-col {
    display: flex;
    flex-direction: column;
    align-items: center;
}
@media (min-width: 768px) {
    .nae-footer .brand-col {
        align-items: flex-start;
    }
}
.nae-footer .brand-col .brand-name {
    font-family: 'Source Serif 4', serif;
    font-size: 20px;
    font-weight: 700;
    color: #171e1e;
    margin: 0 0 8px;
}
.nae-footer .brand-col .tagline {
    font-family: 'Source Serif 4', serif;
    font-style: italic;
    font-size: 16px;
    color: #6a5c4c;
    margin: 0;
}
.nae-footer .link-col {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 16px;
}
@media (min-width: 768px) {
    .nae-footer .link-col {
        align-items: flex-end;
    }
}
.nae-footer .link-row {
    display: flex;
    gap: 32px;
}
.nae-footer .link-row-disabled {
    display: flex;
    gap: 32px;
    justify-content: center;
}
@media (min-width: 768px) {
    .nae-footer .link-row-disabled {
        justify-content: flex-end;
    }
}
.nae-footer .link-row-disabled span {
    font-family: 'Hanken Grotesk', sans-serif;
    font-size: 14px;
    color: #c3c7c7;
    cursor: not-allowed;
}
.st-key-footer_help_row {
    background: #f0eee9;
    margin-top: -68px;
    padding-bottom: 40px;
}
.st-key-footer_help button {
    color: #6a5c4c !important;
    font-family: 'Hanken Grotesk', sans-serif !important;
    font-size: 14px !important;
}
.st-key-footer_help button:hover {
    text-decoration: underline !important;
}
.nae-footer .copyright {
    font-family: 'Hanken Grotesk', sans-serif;
    font-size: 12px;
    color: #737878;
    margin: 0;
}

/* ── Buttons (Stitch 원본 스타일) ────────────────────────── */
button[kind="primary"] {
    background: #171e1e !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 12px !important;
    font-family: 'Hanken Grotesk', sans-serif !important;
    font-size: 18px !important;
    font-weight: 700 !important;
    padding: 16px 40px !important;
    box-shadow: 0 4px 24px -1px rgba(0, 0, 0, 0.03) !important;
}
button[kind="primary"]:hover {
    opacity: 0.9 !important;
}
div[data-testid="stButton"] > button:not([kind="primary"]) {
    background: transparent !important;
    color: #171e1e !important;
    border: 1px solid #737878 !important;
    border-radius: 12px !important;
    font-family: 'Hanken Grotesk', sans-serif !important;
    font-size: 18px !important;
    font-weight: 500 !important;
    padding: 16px 40px !important;
}
</style>
"""


def render_onboarding_page() -> None:
    """첫 실행 환영/온보딩 화면을 렌더링한다."""
    st.markdown(_FONT_LINKS + _STYLE, unsafe_allow_html=True)

    # ── Top Nav ──────────────────────────────────────────────
    # 원본 Stitch 목업은 정적 <a href="#">였다 — 실제 페이지 전환이
    # 되도록 st.button + nav_page 전환 패턴(히어로 버튼과 동일)으로 교체.
    st.markdown('<div class="nae-topnav">', unsafe_allow_html=True)
    brand_col, lib_col, research_col, explore_col, spacer_col, login_col = st.columns(
        [3, 1, 1, 1, 3, 1]
    )
    with brand_col:
        st.markdown('<span class="brand">內書齋</span>', unsafe_allow_html=True)
    with lib_col:
        nav_library = st.button("서재", key="topnav_library", type="tertiary")
    with research_col:
        nav_research = st.button("연구", key="topnav_research", type="tertiary")
    with explore_col:
        nav_explore = st.button("탐색", key="topnav_explore", type="tertiary")
    with login_col:
        # 로그인/계정 기능이 없는 로컬 앱이라 비활성 상태로만 표시한다.
        st.button("로그인", key="topnav_login", type="tertiary", disabled=True)
    st.markdown('</div>', unsafe_allow_html=True)

    if nav_library or nav_research or nav_explore:
        st.session_state["show_onboarding"] = False
        st.session_state["nav_page"] = (
            "Library" if nav_library else "Research" if nav_research else "AI에게 질문"
        )
        st.rerun()

    # ── Hero ─────────────────────────────────────────────────
    st.markdown(
        """
        <div class="nae-hero">
            <div style="margin-bottom: 48px;">
                <div class="classical-title">內書齋</div>
                <div class="classical-subtitle">내서재</div>
            </div>
            <div class="headline" style="text-align: center;">책이 답하고,<br>기록이 말합니다.</div>
            <p class="subheadline">
                개인의 자료와 연구를 하나의 지식으로 연결하는<br>
                목회자를 위한 AI 연구실
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Hero Actions ─────────────────────────────────────────
    _, btn_col1, btn_col2, _ = st.columns([2, 1.4, 1.4, 2])
    with btn_col1:
        start_clicked = st.button("연구 시작하기", use_container_width=True, type="primary")
    with btn_col2:
        load_clicked = st.button("자료 불러오기", use_container_width=True)

    if start_clicked or load_clicked:
        st.session_state["show_onboarding"] = False
        st.session_state["nav_page"] = "Library"
        st.rerun()

    st.write("")
    st.write("")

    # ── Hero Illustration (CSS-only premium art) ─────────────
    st.markdown(
        """
        <div class="nae-hero-illustration">
            <div class="illust-bg"></div>
            <div class="illust-lines"></div>
            <div class="illust-circle"></div>
            <div class="illust-circle"></div>
            <div class="illust-circle"></div>
            <div class="illust-dots">
                <div class="illust-dot"></div>
                <div class="illust-dot"></div>
                <div class="illust-dot"></div>
            </div>
            <div class="overlay"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.write("")
    st.write("")

    # ── Feature Cards ────────────────────────────────────────
    st.markdown('<div class="nae-section-title">내서재가 하는 일</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="nae-features-section">', unsafe_allow_html=True)
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
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Quote ────────────────────────────────────────────────
    st.markdown(
        """
        <div class="nae-quote-section">
            <div class="nae-quote">
                <div class="rule"></div>
                <blockquote>"책을 읽는 것은 대화하는 것이다.<br> 지혜의 거장들과 대화하며<br>나의 신학을 세워가는 이 거룩한 노동을 돕습니다."</blockquote>
                <div class="rule"></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.write("")
    skip_clicked = st.button("나중에 하기", key="_onboard_skip")
    if skip_clicked:
        st.session_state["show_onboarding"] = False
        st.rerun()

    # ── Footer ───────────────────────────────────────────────
    # "이용약관"/"개인정보처리방침"은 아직 실제 문서가 없어 비활성 텍스트로
    # 표시한다("로그인" 버튼과 동일한 처리). "도움말"은 실제 화면이 있어
    # 클릭 시 이동하는 버튼으로 교체(원본 Stitch 목업의 <a href="#">를 대체).
    st.markdown(
        """
        <div class="nae-footer">
            <div class="footer-inner">
                <div class="brand-col">
                    <span class="brand-name">內書齋</span>
                    <p class="tagline">"생각을 쌓고, 말씀을 잇다."</p>
                </div>
                <div class="link-col">
                    <div class="link-row-disabled">
                        <span>이용약관</span>
                        <span>개인정보처리방침</span>
                    </div>
        """,
        unsafe_allow_html=True,
    )
    with st.container(key="footer_help_row"):
        _, help_col = st.columns([5, 1])
        with help_col:
            help_clicked = st.button("도움말", key="footer_help", type="tertiary")
    st.markdown(
        """
                    <p class="copyright">© 2026 NAE. Powered by NAE</p>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if help_clicked:
        st.session_state["show_onboarding"] = False
        st.session_state["nav_page"] = "도움말"
        st.rerun()
