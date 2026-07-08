"""DBMA Design System — Research Workspace Page.

Search, retrieval, and document analysis interface for research workflow.
"""

from typing import Optional

import streamlit as st
from pathlib import Path

from ui.pages._base import BasePage
from ui.theme.colors import THEME
from ui.components.tables import search_results_table
from ui.state.store import StateStore
from core.config import DEFAULT_OUTPUT_DIR


def render_research_page() -> None:
    """Render the DBMA Research Workspace page."""
    page = BasePage(title="Research Workspace", icon="🔬")
    page.render_header()

    # ── Search Interface ───────────────────────────────────────
    page.render_section("검색", icon="🔍")
    _render_search_interface()

    # ── Search Results ─────────────────────────────────────────
    page.render_section("검색 결과", icon="📊")
    _render_search_results()

    # ── Query Analysis ─────────────────────────────────────────
    page.render_section("쿼리 분석", icon="📈")
    _render_query_analysis()

    page.render_footer()


def _render_search_interface() -> None:
    """Render the search input interface."""
    store = StateStore()

    # Primary search input
    query = st.text_area(
        "검색 쿼리 입력",
        placeholder="연구 주제, 키워드 또는 질문을 입력하세요...",
        height=80,
        key="research_query",
    )

    if query:
        store.set("research_query", query)

    # Search options
    c1, c2, c3 = st.columns(3)
    with c1:
        top_k = st.slider(
            "결과 수 (K)",
            min_value=1,
            max_value=50,
            value=10,
            step=1,
            key="research_top_k",
        )
    with c2:
        method = st.selectbox(
            "검색 방법",
            options=["RRF", "BM25", "Vector", "Hybrid"],
            key="search_method",
        )
    with c3:
        min_score = st.slider(
            "최소 점수",
            min_value=0.0,
            max_value=1.0,
            value=0.1,
            step=0.05,
            key="min_score",
        )

    # Execute search button
    st.divider()
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🔍 검색 실행", type="primary", use_container_width=True):
            st.success("검색이 완료되었습니다!")
            # TODO: trigger retrieval pipeline


def _render_search_results() -> None:
    """Render the search results display."""
    # Simulated search results (replace with actual pipeline output)
    results = _get_simulated_results()

    if not results:
        st.info("검색 결과를 확인하세요.")
        return

    # Display result count and sort option
    c1, c2 = st.columns([3, 1])
    with c1:
        st.caption(f"총 {len(results)}개의 결과")
    with c2:
        sort_option = st.selectbox(
            "정렬",
            options=["relevance", "date", "title"],
            label_visibility="collapsed",
            key="result_sort",
        )

    # Render search results table
    search_results_table(
        results=results,
        score_column="score",
        highlight_query=st.session_state.get("research_query", ""),
    )


def _render_query_analysis() -> None:
    """Render the query analysis panel."""
    query = st.session_state.get("research_query", "")

    if not query:
        st.info("쿼리를 입력하여 분석 결과를 확인하세요.")
        return

    # Query statistics
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("문자 수", len(query))
    with c2:
        st.metric("단어 수", len(query.split()))
    with c3:
        st.metric("검색어 분리", len([w for w in query.split() if len(w) > 1]))
    with c4:
        st.metric("추출된 엔티티", "3")

    # Query expansion suggestions
    st.markdown("### 💡 검색어 확장 제안")
    suggestions = [
        f"{query} 관련 문헌",
        f"{query.split()[0] if query.split() else ''} 논평",
        f"{query} 신학적 분석",
    ]
    for s in suggestions:
        st.caption(f"• {s}")


def _get_simulated_results() -> list[dict]:
    """Get simulated search results (replace with actual pipeline)."""
    query = st.session_state.get("research_query", "")

    if not query:
        return []

    # Simulated results based on output directory
    output_dir = Path(DEFAULT_OUTPUT_DIR)
    results = []

    if output_dir.exists():
        for md_file in list(output_dir.rglob("*.md"))[:5]:
            stem = md_file.stem
            if stem.endswith("_chunks"):
                stem = stem[:-7]

            results.append({
                "title": stem,
                "score": 0.85 - (results.__len__() * 0.05),
                "type": "md",
                "snippet": f"이 문서는 {stem}에 대한 내용을 포함하고 있습니다...",
                "source": str(md_file.relative_to(Path.cwd())),
            })

    return results