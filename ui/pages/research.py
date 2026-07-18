"""DBMA Design System — Research Workspace Page.

Search, retrieval, and document analysis interface for research workflow.
Connects UI to production Retrieval Engine (core/retrieval.py).
"""

from typing import Optional

import streamlit as st
from pathlib import Path

from ui.pages._base import BasePage
from ui.theme.colors import THEME
from ui.components.tables import search_results_table
from ui.state.store import StateStore
from core.config import DEFAULT_OUTPUT_DIR

# Production retrieval imports (LOOP 3 — binding)
from core.retrieval import QueryProcessor, RetrievalEngine, RankedCandidate
from ui.state.query_processor import get_shared_query_processor


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


def _execute_research_query(query: str, top_k: int) -> tuple[list[dict], object | None, str]:
    """
    Execute a research query through the production Retrieval Engine.

    This is the primary binding function connecting Research UI to core/retrieval.py.

    Args:
        query: User's research query string.
        top_k: Number of results to return.

    Returns:
        (results_list, response_object, status_message) tuple.
        On success: ([formatted_results], ResponsePackage, "검색 완료")
        On error/empty: ([], None, "에러: {message}" or "쿼리를 입력하세요")
    """
    # Validate query
    if not query or not query.strip():
        return [], None, "쿼리를 입력하세요"

    query = query.strip()

    try:
        # [SPRINT17-Phase5-M1b-2.1] Shared across all pages that need a
        # QueryProcessor (Research, Chat) — one RetrievalEngine instance
        # per session instead of one per page. [SPRINT21-G Gap#1] recreated
        # automatically when the TSU dataset on disk changes — see
        # ui/state/query_processor.py.
        processor: QueryProcessor = get_shared_query_processor()

        # Execute retrieval pipeline
        response = processor.process(query, query_id="research-ui", k=top_k)

        # Check for results
        if not response.top_k_results:
            return [], None, f"결과 없음 (쿼리: {query})"

        # Format candidates for UI display
        results = []
        for candidate in response.top_k_results:
            formatted = _format_candidate(candidate, response.parsed_query)
            results.append(formatted)

        return results, response, f"검색 완료 ({len(results)}개 결과)"

    except FileNotFoundError as e:
        return [], None, f"에러: TSU 데이터셋을 찾을 수 없습니다 — {str(e)}"
    except Exception as e:
        return [], None, f"에러: 검색 실행 중 오류 발생 — {str(e)}"


def _format_candidate(candidate: RankedCandidate, parsed_query) -> dict:
    """
    Map a production RankedCandidate to UI display format.

    Transforms core/retrieval.py data models into the dictionary format
    expected by search_results_table() component.
    """
    # Build verse reference string from metadata
    vm = candidate.metadata.get("verse_mapping", {})
    if vm and vm.get("book_id"):
        book_id = vm["book_id"]
        chapter = vm.get("chapter", "?")
        v_start = vm.get("verse_start", "?")
        v_end = vm.get("verse_end", v_start)
        verse_ref = f"{book_id} {chapter}:{v_start}"
        if v_end and v_end != v_start:
            verse_ref += f"-{v_end}"
    else:
        verse_ref = "Unmapped passage"

    # Build title from reference + content preview
    content_preview = candidate.content[:120].replace("\n", " ")
    title = f"{verse_ref} — {content_preview}..."

    # Get source file from metadata
    source_file = candidate.metadata.get("source_file", "Unknown source")

    return {
        "title": title,
        "score": candidate.final_score,
        "type": "tsu",
        "snippet": candidate.content[:300].replace("\n", " "),
        "source": source_file,
        # Extended metadata for detailed display
        "tsu_id": candidate.tsu_id,
        "bm25_score": candidate.bm25_score,
        "vector_score": candidate.vector_score,
        "theological_score": candidate.theological_score,
        "verse_mapping": verse_ref,
        "explanation": candidate.explanation,
    }


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
            options=["Hybrid", "BM25", "Vector", "RRF"],
            key="search_method",
        )
    with c3:
        min_score = st.slider(
            "최소 점수",
            min_value=0.0,
            max_value=1.0,
            value=0.0,
            step=0.05,
            key="min_score",
        )

    # Execute search button — connected to production retrieval (LOOP 3)
    st.divider()
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🔍 검색 실행", type="primary", use_container_width=True):
            user_query = st.session_state.get("research_query", "")
            user_top_k = st.session_state.get("research_top_k", 10)

            # Execute production retrieval
            results, response_obj, status_msg = _execute_research_query(user_query, user_top_k)

            # Store results in session state for display
            st.session_state["research_results"] = results
            st.session_state["search_status"] = status_msg
            st.session_state["research_response"] = response_obj  # For query analysis

            # Show visual feedback
            if "에러" in status_msg:
                st.error(status_msg)
            elif "결과 없음" in status_msg:
                st.warning(status_msg)
            else:
                st.success(status_msg)


def _render_search_results() -> None:
    """Render the search results display from production retrieval."""
    # Read results from session state (set by search button click)
    results = st.session_state.get("research_results", [])

    if not results:
        status = st.session_state.get("search_status", "")
        if status:
            # Status already displayed in search interface
            pass
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

    # Intent detection from production pipeline (if available)
    intent = "unknown"
    detected_books = []
    if "research_response" in st.session_state:
        resp = st.session_state["research_response"]
        if hasattr(resp, "parsed_query"):
            intent = getattr(resp.parsed_query, "intent", "unknown")
            detected_books = getattr(resp.parsed_query, "detected_books", [])

    with c4:
        intent_display = intent.upper() if intent != "unknown" else "—"
        st.metric("인식된 의도", intent_display)

    # Query expansion suggestions
    st.markdown("### 💡 검색어 확장 제안")
    first_word = query.split()[0] if query.split() else ""
    suggestions = [
        f"{query} 관련 문헌",
        f"{first_word} 논평",
        f"{query} 신학적 분석",
    ]
    for s in suggestions:
        st.caption(f"• {s}")

    # Display scripture references if detected (LOOP 3 enhancement)
    if detected_books:
        st.markdown("### 📖 감지된 성서 도서")
        col1, col2 = st.columns(2)
        with col1:
            st.caption(f"감지된 도서: {', '.join(detected_books)}")