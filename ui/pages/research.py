"""DBMA Design System — Research Workspace Page (Stitch Style).

Search, retrieval, and document analysis interface for research workflow.
Connects UI to production Retrieval Engine (core/retrieval.py).

Stitch-style redesign:
- Rounded search bar with AI-powered suggestions
- Insight cards for query analysis
- Card-based result display with score badges
- Session management with expandable history
"""

from dataclasses import dataclass
from typing import Optional

import streamlit as st
from pathlib import Path

from ui.pages._base import BasePage
from ui.theme.colors import THEME
from ui.state.store import StateStore
from core.config import DEFAULT_OUTPUT_DIR

# Production retrieval imports (LOOP 3 — binding)
from core.retrieval import QueryProcessor, RetrievalEngine, RankedCandidate
from ui.state.query_processor import get_shared_query_processor, record_query_latency
from core.research_workspace import add_query_result, create_session, list_sessions, load_session

# [DBMA-SEARCH-INFRA-001 HQ 제안 ⑨] Top1/Top5 click tracking — only
# meaningful when USE_INVERTED_INDEX routes through HybridQueryProcessor
# (core.retrieval.QueryProcessor's ResponsePackage has no telemetry_query_id,
# so _record_result_click() below no-ops for the legacy path).
from core.search_telemetry import open_telemetry


def _record_result_click(tsu_id: str, rank: int) -> None:
    response_obj = st.session_state.get("research_response")
    query_record_id = getattr(response_obj, "telemetry_query_id", None)
    if query_record_id is None:
        return
    try:
        telemetry = open_telemetry()
        telemetry.record_click(query_record_id, tsu_id=tsu_id, rank=rank)
        telemetry.close()
    except Exception:
        pass  # telemetry is best-effort — never block the click itself


# ── Data Classes ────────────────────────────────────────────────

@dataclass
class SearchResultCard:
    """Search result card configuration."""
    rank: int
    title: str
    score: float
    doc_type: str
    snippet: str
    source: str
    source_file: str = ""
    document_id: str = ""
    tsu_id: str = ""
    verse_mapping: str = ""
    explanation: str = ""
    bm25_score: float = 0.0
    vector_score: float = 0.0
    theological_score: float = 0.0


@dataclass
class QueryInsight:
    """Query analysis insight card."""
    title: str
    icon: str
    content: str
    color: str = THEME.TEXT_LINK


# ── Style Functions ─────────────────────────────────────────────

def _apply_research_styles() -> None:
    """연구하기 워크스페이스 Stitch 화면 스타일 — 둥근 검색창, AI 인사이트 카드."""
    st.markdown(
        f"""
        <style>
        /* Rounded search textarea */
        div[data-testid="stTextArea"] textarea {{
            border-radius: 16px !important;
            border-color: {THEME.BORDER_MEDIUM} !important;
            font-family: 'Source Serif 4', serif;
            font-size: 15px;
            padding: 16px 20px;
        }}
        div[data-testid="stTextArea"] textarea:focus {{
            border-color: {THEME.BRAND_PRIMARY} !important;
            box-shadow: 0 0 0 2px {THEME.BRAND_PRIMARY}22 !important;
        }}

        /* Insight cards */
        .research-insight-card {{
            background: {THEME.TEXT_LINK}14;
            border: 1px solid {THEME.TEXT_LINK}33;
            border-radius: 12px;
            padding: 16px 20px;
            margin-bottom: 12px;
        }}

        /* Session cards */
        .research-session-card {{
            background: {THEME.BG_SURFACE};
            border: 1px solid {THEME.BORDER_LIGHT};
            border-radius: 8px;
            padding: 12px 16px;
            margin-bottom: 8px;
        }}

        /* Expander styling */
        div[data-testid="stExpander"] {{
            border: 1px solid {THEME.BORDER_LIGHT} !important;
            border-radius: 12px !important;
        }}

        /* Metric cards */
        [data-testid="stMetric"] {{
            background-color: {THEME.BG_SURFACE};
            padding: 0.5rem 1rem;
            border-radius: 8px;
            border: 1px solid {THEME.BORDER_LIGHT};
        }}

        /* Divider styling */
        hr {{
            margin: 1.5rem 0 !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# ── Main Render Function ───────────────────────────────────────

def render_research_page() -> None:
    """Render the DBMA Research Workspace page (Stitch style)."""
    _apply_research_styles()
    
    # [SPRINT27-E] One research session per browser visit (ADR-005 §1)
    if "research_session_id" not in st.session_state:
        st.session_state["research_session_id"] = create_session()

    detail_selection = st.session_state.get("research_detail_selection")
    if detail_selection is not None:
        _render_research_page_with_detail()
    else:
        page = BasePage(title="연구 공간", icon="🧪")
        page.render_header()

        # ── Search Interface ───────────────────────────────────
        page.render_section("검색", icon="🔍")
        _render_search_interface()

        # ── Search Results ─────────────────────────────────────
        page.render_section("검색 결과", icon="📊")
        _render_search_results()

        # ── Query Analysis ─────────────────────────────────────
        page.render_section("쿼리 분석", icon="📈")
        _render_query_analysis()

        page.render_footer()


# ── Search Interface ───────────────────────────────────────────

def _render_search_interface() -> None:
    """Render the search input interface (Stitch style)."""
    store = StateStore()

    # Primary search input — rounded search bar
    query = st.text_area(
        "",  # Empty label for Stitch style (placeholder only)
        value=st.session_state.get("research_query", ""),
        placeholder="연구 주제, 키워드 또는 질문을 입력하세요...",
        height=100,
        key="research_query",
    )

    if query:
        store.set("research_query", query)

    # Search options — compact row
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        top_k = st.slider(
            "결과 수 (K)",
            min_value=1,
            max_value=50,
            value=st.session_state.get("research_top_k", 10),
            step=1,
            key="research_top_k",
        )
    with c2:
        method = st.selectbox(
            "검색 방법",
            options=["Hybrid", "BM25", "Vector", "RRF"],
            index=["Hybrid", "BM25", "Vector", "RRF"].index(
                st.session_state.get("search_method", "Hybrid")
            ),
            key="search_method",
        )
    with c3:
        min_score = st.slider(
            "최소 점수",
            min_value=0.0,
            max_value=1.0,
            value=st.session_state.get("min_score", 0.0),
            step=0.05,
            key="min_score",
        )

    # Execute search button
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


# ── Search Results ─────────────────────────────────────────────

def _render_search_results() -> None:
    """Render the search results display (Stitch style cards)."""
    results = st.session_state.get("research_results", [])

    if not results:
        status = st.session_state.get("search_status", "")
        if status:
            pass
        st.info("검색어를 입력하고 '검색 실행'을 클릭하세요.")
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

    # Render search results as Stitch-style cards
    _render_search_results_as_cards(results)
    
    # Session save
    st.divider()
    st.subheader("세션 저장")
    if st.button("📌 세션에 저장", type="secondary", use_container_width=True):
        query = st.session_state.get("research_query", "")
        response_obj = st.session_state.get("research_response")
        
        if query and response_obj:
            try:
                session_id = st.session_state["research_session_id"]
                success = add_query_result(session_id, query, response_obj.to_dict())
                
                if success:
                    st.success(f"세션 저장 완료! (ID: {session_id[:8]}...)")
                else:
                    st.error("세션 저장에 실패했습니다.")
            except Exception as e:
                st.error(f"세션 저장 중 오류 발생: {str(e)}")
        else:
            st.warning("저장할 검색 결과가 없습니다.")

    _render_saved_sessions()


def _render_search_results_as_cards(results: list[dict]) -> None:
    """Render search results as Stitch-style cards with score badges."""
    for i, result in enumerate(results):
        score = result.get("score", 0)
        title = result.get("title", "미제시")
        doc_type = result.get("type", "document").upper()
        snippet = result.get("snippet", "")
        source = result.get("source", "")

        # Score badge color
        if score >= 0.8:
            score_color = THEME.STATUS_SUCCESS
        elif score >= 0.5:
            score_color = THEME.STATUS_WARNING
        else:
            score_color = THEME.STATUS_ERROR

        html = f"""
        <div style="
            background: {THEME.BG_SURFACE};
            border: 1px solid {THEME.BORDER_LIGHT};
            border-radius: 12px;
            padding: 16px 20px;
            margin-bottom: 12px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        ">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
                <span style="font-size: 15px; font-weight: 600; color: {THEME.BRAND_PRIMARY};">
                    {i + 1}. {title}
                </span>
                <span style="
                    font-size: 12px; font-weight: 700; padding: 4px 10px; border-radius: 8px;
                    background: {score_color}18; color: {score_color};
                ">
                    RRF {score:.4f}
                </span>
            </div>
            <div style="font-size: 11px; color: {THEME.TEXT_TERTIARY}; margin-bottom: 8px;">
                {doc_type}
                {f' • {source}' if source else ''}
            </div>
            {f'<div style="font-family: Source Serif 4, serif; font-style: italic; font-size: 14px; color: {THEME.TEXT_SECONDARY}; line-height: 1.6;">{snippet}</div>' if snippet else ''}
        </div>
        """
        st.markdown(html, unsafe_allow_html=True)

        # Clickable source button
        source_file = result.get("source_file", "")
        document_id = result.get("document_id", "")
        if source_file or document_id:
            btn_key = f"nav_res_{i}_{abs(hash(result.get('tsu_id', ''))) & 0xFFFFFFFF:x}"
            research_query = st.session_state.get("research_query", "")
            query_terms = research_query.split() if research_query else []

            if st.button(
                f"📄 {source_file}",
                key=btn_key,
                type="primary",
                use_container_width=True,
            ):
                _record_result_click(result.get("tsu_id", ""), rank=i + 1)
                st.session_state["research_detail_selection"] = {
                    "source_file": source_file,
                    "document_id": document_id,
                    "query_terms": query_terms,
                }
                st.rerun()

            score = result.get("score", 0.0)
            st.caption(f"신뢰도: {score:.4f}")


# ── Saved Sessions ─────────────────────────────────────────────

def _render_saved_sessions() -> None:
    """Render a read-only list of saved research sessions."""
    st.divider()
    st.subheader("저장된 세션")

    sessions = list_sessions()
    if not sessions:
        st.caption("저장된 세션이 없습니다.")
        return

    sessions_sorted = sorted(sessions, key=lambda s: s.get("created_at", ""), reverse=True)
    options = {
        f"{s.get('created_at', s.get('session_id', '?'))} · 쿼리 {len(s.get('queries', []))}개": s.get("session_id")
        for s in sessions_sorted
    }
    selected_label = st.selectbox(
        "세션 선택",
        options=list(options.keys()),
        key="research_selected_session_label",
    )
    session_id = options.get(selected_label)

    session = load_session(session_id) if session_id else None
    if not session:
        st.caption("세션을 불러올 수 없습니다.")
        return

    for i, q in enumerate(session.get("queries", [])):
        with st.expander(f"{q.get('timestamp', '?')} — {q.get('query', '')}"):
            refs = q.get("result_refs", [])
            if refs:
                st.caption(f"저장된 참조 {len(refs)}건")
                st.table(refs)
            else:
                st.caption("저장된 참조 없음")

            if st.button("이 쿼리 불러오기", key=f"load_query_{session_id}_{i}"):
                st.session_state["research_query"] = q.get("query", "")
                st.success("쿼리를 검색창에 불러왔습니다. '검색 실행'을 눌러 재검색하세요.")


# ── Query Analysis ─────────────────────────────────────────────

def _render_query_analysis() -> None:
    """Render the query analysis panel (Stitch insight cards)."""
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

    # Intent detection from production pipeline
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

    # Query expansion suggestions — AI Insight card (Stitch style)
    first_word = query.split()[0] if query.split() else ""
    suggestions = [
        f"{query} 관련 문헌",
        f"{first_word} 논평",
        f"{query} 신학적 분석",
    ]
    suggestions_html = "".join(f"<div>• {s}</div>" for s in suggestions)
    
    _render_insight_card(
        title="🧪 검색어 확장 제안",
        content=suggestions_html,
    )

    # Display scripture references if detected
    if detected_books:
        books_html = f"{', '.join(detected_books)}"
        _render_insight_card(
            title="📖 감지된 성서 도서",
            content=books_html,
            color=THEME.BRAND_SECONDARY,
        )


def _render_insight_card(title: str, content: str, color: str = THEME.TEXT_LINK) -> None:
    """Render an AI insight card (Stitch style)."""
    st.markdown(
        f"""
        <div class="research-insight-card" style="border-left: 4px solid {color};">
            <div style="font-weight: 600; color: {THEME.TEXT_PRIMARY}; margin-bottom: 8px;">
                {title}
            </div>
            <div style="font-size: 13px; color: {THEME.TEXT_SECONDARY}; line-height: 1.8;">
                {content}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Production Retrieval Binding ───────────────────────────────

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
        # automatically when the TSU dataset on disk changes.
        processor: QueryProcessor = get_shared_query_processor()

        # Execute retrieval pipeline
        response = processor.process(query, query_id="research-ui", k=top_k)
        record_query_latency(response.performance_metrics.total_ms)

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
        # DBMA-UI-NAV-001: Source navigation metadata
        "source_file": source_file,
        "document_id": candidate.metadata.get("document_id", ""),
        # Extended metadata for detailed display
        "tsu_id": candidate.tsu_id,
        "bm25_score": candidate.bm25_score,
        "vector_score": candidate.vector_score,
        "theological_score": candidate.theological_score,
        "verse_mapping": verse_ref,
        "explanation": candidate.explanation,
    }


# ── Detail Panel Layout ────────────────────────────────────────

def _render_research_page_with_detail() -> None:
    """2단 레이아웃: 왼쪽 검색/결과, 오른쪽 문서 상세 패널."""
    from core.document_detail import get_document_detail
    from ui.components.detail_panel import render_detail_panel

    detail_selection = st.session_state.get("research_detail_selection")
    if detail_selection is None:
        return

    source_file = detail_selection["source_file"]
    document_id = detail_selection["document_id"]
    query_terms = detail_selection.get("query_terms", [])

    cols = st.columns([2, 1])
    with cols[0]:
        page = BasePage(title="연구 공간", icon="🧪")
        page.render_header()

        page.render_section("검색", icon="🔍")
        _render_search_interface()

        page.render_section("검색 결과", icon="📊")
        _render_search_results()

        page.render_section("쿼리 분석", icon="📈")
        _render_query_analysis()

        page.render_footer()

    with cols[1]:
        # Close button
        if st.button("닫기", key="research_detail_close_btn", type="primary"):
            st.session_state["research_detail_selection"] = None
            st.rerun()

        st.divider()

        # Document detail info
        detail = get_document_detail(
            source_file=source_file,
            document_id=document_id,
            query_terms=query_terms,
        )

        # Render detail panel
        render_detail_panel(detail, query_terms)