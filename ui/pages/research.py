"""DBMA Design System — Research Workspace Page (Stitch Style).

Search, retrieval, and document analysis interface for research workflow.
Connects UI to production Retrieval Engine (core/retrieval.py).

Stitch-style redesign:
- Rounded search bar with AI-powered suggestions
- Insight cards for query analysis
- Card-based result display with score badges
- Session management with expandable history
"""

import logging
import os
from dataclasses import dataclass
from typing import Any, Optional

import streamlit as st
from pathlib import Path

from ui.pages._base import BasePage
from ui.theme.colors import THEME
from ui.state.store import StateStore
from core.config import DEFAULT_OUTPUT_DIR

logger = logging.getLogger(__name__)

# Production retrieval imports (LOOP 3 — binding)
from core.retrieval import QueryProcessor, RetrievalEngine, RankedCandidate, Citation
from ui.state.query_processor import get_shared_query_processor, record_query_latency
from core.research_workspace import add_query_result, create_session, list_sessions, load_session
from ui.components.citation_card import render_citation_card
from ui.pages.chat import generate_answer

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
        page = BasePage(title="연구 공간", icon="science")
        page.render_header()

        # ── Search Interface ───────────────────────────────────
        page.render_section("검색", icon="search")
        _render_search_interface()

        # ── AI Answer (always alongside search results) ────────
        page.render_section("AI 답변", icon="lightbulb")
        _render_ai_answer()

        # ── Search Results ─────────────────────────────────────
        page.render_section("참고한 자료", icon="bar_chart")
        _render_search_results()

        # ── NAE Public Theology (ADR-024 Bridge) ───────────────
        # nae_pd module이 enabled일 때만 표시 — §F module gating 준수
        _render_nae_section()

        # ── Query Analysis ─────────────────────────────────────
        page.render_section("검색 분석", icon="trending_up")
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
        placeholder="성경 구절, 주제, 질문을 입력하세요…",
        height=100,
        key="research_query",
    )

    if query:
        store.set("research_query", query)

    # [DBMA-UX-004] "검색 방법"(Hybrid/BM25/Vector/RRF)과 "최소 점수"는
    # 검색 엔진 내부 알고리즘/relevance-score 파라미터라 일반 사용자에게
    # 노출하지 않는다(Design Brief §8, "Vector" 등은 금지 용어 목록에
    # 직접 해당). ui/app.py Monitor·ui/pages/library.py 청킹 미리보기와
    # 동일한 패턴으로 NAE_ADMIN_MODE=1일 때만 노출하고, 일반 사용자는
    # 안전한 기본값(Hybrid, 0.0)을 그대로 쓴다. "결과 수"만 남긴다 —
    # "몇 건 보여줄지"는 목회자도 이해할 수 있는 개념이라 유지.
    is_admin = os.environ.get("NAE_ADMIN_MODE") == "1"
    if is_admin:
        c1, c2, c3 = st.columns([2, 1, 1])
    else:
        c1, = st.columns([2])
        c2 = c3 = None
    with c1:
        top_k = st.slider(
            "결과 수",
            min_value=1,
            max_value=50,
            value=st.session_state.get("research_top_k", 10),
            step=1,
            key="research_top_k",
        )
    if is_admin:
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
    else:
        st.session_state.setdefault("search_method", "Hybrid")
        st.session_state.setdefault("min_score", 0.0)

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

            # Always run AI answer path alongside search (UX-007 §4.1)
            try:
                answer_text, _sources = generate_answer(
                    user_query, conversation_history="", k=user_top_k
                )
                st.session_state["research_ai_answer"] = answer_text if answer_text else ""
            except Exception as e:
                logger.warning("AI answer generation failed in research page: %s", e)
                st.session_state["research_ai_answer"] = ""

            # Show visual feedback
            if "에러" in status_msg:
                st.error(status_msg)
            elif "결과 없음" in status_msg:
                st.warning(status_msg)
            else:
                st.success(status_msg)


# ── AI Answer ────────────────────────────────────────────────


def _render_ai_answer() -> None:
    """Render the AI-generated answer block.

    Always called (UX-007 §4.1) — shows nothing when no answer is available,
    never blocks search results from rendering.
    """
    answer = st.session_state.get("research_ai_answer", "")
    if not answer:
        st.caption("검색어를 입력하고 '검색 실행'을 클릭하세요.")
        return
    st.markdown(answer)


# ── Search Results ───────────────────────────────────────────────

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
            options=["관련도순", "날짜순", "제목순"],
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
        title = result.get("title", "제목 없음")
        snippet = result.get("snippet", "")
        source_file = result.get("source_file", "")
        document_id = result.get("document_id", "")

        # 제목/순번 헤더 — 카드 밖에 별도 표시 (render_citation_card에 title 파라미터 없음)
        st.markdown(f"**{i + 1}. {title}**")

        # Citation card — 별점 배지 + 저자/출처/근거신뢰도 메타 줄을 위임
        render_citation_card(
            source_file=source_file,
            text_location=None,  # research.py 결과엔 heading_path 없음
            doc_type=None,        # doc_type이 "tsu" 고정이라 표시 가치 없음
            author=result.get("author") or None,
            citation_title=result.get("source_title") or None,
            relevance_score=score,
            on_view_original=False,  # 내비게이션은 아래 "📄" 버튼이 담당 — 중복 버튼 금지
            on_copy_citation=False,
        )

        # 발췌문 — 카드 밖에 별도 표시 (render_citation_card에 snippet 파라미터 없음)
        if snippet:
            st.markdown(
                f'<div style="font-family: Source Serif 4, serif; font-style: italic; '
                f'font-size: 14px; color: {THEME.TEXT_SECONDARY}; line-height: 1.6;">{snippet}</div>',
                unsafe_allow_html=True,
            )

        # Clickable source button (무변경 — tests/test_sermon_research_hub.py 의존)
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

        _render_send_to_sermon_research_button(result, i)


def _render_send_to_sermon_research_button(result: dict, index: int) -> None:
    """UX-007 §13 설계(Tier B) — 검색 결과를 설교 연구 허브로 보낸다.
    §4.5: 클릭 시 화면은 그대로 유지(이동하지 않음). 전환 버퍼는
    sermon_research_selection(신규 session_state 키) — 허브 화면이
    열릴 때 흡수한다. 참고: docs/DBMA-UX-007-SessionState-Design.md §2.1"""
    tsu_id = result.get("tsu_id", "")
    btn_key = f"send_sermon_{index}_{abs(hash(tsu_id)) & 0xFFFFFFFF:x}"
    if st.button("설교 연구에 추가", key=btn_key, use_container_width=True):
        import datetime

        st.session_state.setdefault("sermon_research_selection", [])
        st.session_state["sermon_research_selection"].append({
            "tsu_id": tsu_id,
            "document_id": result.get("document_id", ""),
            "excerpt": result.get("snippet", ""),
            "source_label": result.get("source", ""),
            "added_at": datetime.datetime.now().isoformat(timespec="seconds"),
        })
        st.toast("설교 연구에 추가되었습니다")


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
        f"{s.get('created_at', s.get('session_id', '?'))} · 검색 {len(s.get('queries', []))}건": s.get("session_id")
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

            if st.button("이 검색어 불러오기", key=f"load_query_{session_id}_{i}"):
                st.session_state["research_query"] = q.get("query", "")
                st.success("검색어를 검색창에 불러왔습니다. '검색 실행'을 눌러 재검색하세요.")


# ── NAE Public Theology Bridge (ADR-024) ────────────────────────

def _render_nae_section() -> None:
    """NAE Public Theology 검색 섹션 — module gating 준수 (§F).

    nae_pd가 disabled면 이 함수가 아무것도 렌더링하지 않는다.
    enabled일 때만 "NAE Public Theology (Beta)" 섹션을 표시하고,
    DBMA 결과와 별도 영역으로 보여준다 (§B 병합 금지).
    """
    from core import module_registry

    if not module_registry.is_enabled("nae_pd"):
        return  # §F: disabled면 렌더링하지 않음

    st.divider()
    st.subheader("📖 NAE Public Theology (Beta)")
    st.caption("공개 신학 corpus — DBMA 결과와 별도 검색")

    # NAE 전용 검색어 입력 (DBMA 검색어와 분리)
    nae_query = st.text_input(
        "NAE 검색어",
        placeholder="NAE corpus에서 검색할 질문을 입력하세요...",
        key="nae_research_query",
    )

    if not nae_query:
        st.info("NAE 검색어를 입력하고 '검색'을 클릭하세요.")
        return

    # NAE 검색 실행 버튼
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🔍 NAE 검색", type="primary", use_container_width=True):
            nae_results = _execute_nae_retrieval(nae_query)
            st.session_state["nae_research_results"] = nae_results
            st.session_state["nae_search_status"] = (
                f"NAE 결과 {len(nae_results)}건" if nae_results else "NAE 결과 없음"
            )

    # NAE 결과 표시
    nae_results = st.session_state.get("nae_research_results")
    nae_status = st.session_state.get("nae_search_status", "")

    if not nae_results and not nae_status:
        return

    if nae_status:
        st.caption(nae_status)

    if not nae_results:
        st.info("NAE corpus에서 일치하는 결과가 없습니다.")
        return

    # NAE 결과 카드 표시
    for i, citation in enumerate(nae_results, 1):
        score = getattr(citation, "retrieval_score", 0)
        author = getattr(citation, "source_author", "") or "Unknown"
        excerpt = getattr(citation, "content_excerpt", "") or ""
        scripture = getattr(citation, "scripture_reference", "Unmapped")
        source_title = getattr(citation, "source_title", "") or "Unknown Work"

        with st.container():
            st.markdown(f"**{i}. {source_title}**")
            st.caption(f"Score: {score:.4f} | {scripture}")
            st.caption(f"Author: {author}")
            st.caption(excerpt[:300])
            if getattr(citation, "tsu_id", None):
                st.caption(f"출처 ID: {citation.tsu_id}")


def _execute_nae_retrieval(query: str) -> list[Any]:
    """NAE Qdrant 검색 실행 — bridge_query() 호출.

    §G fail-closed: 모든 예외를 캐치하고 [] 반환.
    """
    try:
        from NAE.retrieval_adapter import bridge_query, NaePdModuleDisabledError

        # module gate는 bridge_query 내부에서 처리 — limit_check=True (기본값)
        citations = bridge_query(query, top_k=10, limit_check=True)
        return citations or []

    except NaePdModuleDisabledError:
        # 설정 오류 — UI가 구분해서 보여줘야 함
        st.error("NAE 모듈이 비활성화되었습니다. config.yaml에서 nae_pd.enabled: true로 설정하세요.")
        return []

    except Exception:  # noqa: BLE001 — §G fail-closed
        st.warning("NAE 검색 중 오류가 발생했습니다. (fail-closed: 빈 결과)")
        return []


# ── Query Analysis ─────────────────────────────────────────────

def _render_query_analysis() -> None:
    """Render the query analysis panel (Stitch insight cards)."""
    query = st.session_state.get("research_query", "")

    if not query:
        st.info("검색어를 입력하면 분석 결과를 볼 수 있습니다.")
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

    # [DBMA-UX-004] ParsedQuery.intent is an internal classification code
    # (core/retrieval.py) — translate to plain Korean instead of showing
    # the raw enum string (was rendering e.g. "EXEGESIS", "CROSS-REFERENCE").
    _INTENT_LABELS = {
        "exegesis": "본문 해석",
        "comparison": "비교",
        "devotional": "묵상",
        "theological": "신학적 고찰",
        "cross-reference": "관련 구절",
    }
    with c4:
        intent_display = _INTENT_LABELS.get(intent, "—")
        st.metric("찾으시는 내용", intent_display)

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
        # [DBMA-UX-004] detected_books는 원시 book_id 코드(예: "ROM")라
        # 그대로 노출하지 않고 한글 성경 이름으로 변환한다.
        from core.sermon.bible_books import BIBLE_BOOKS
        _BOOK_ID_TO_NAME = {book_id: name for name, book_id in BIBLE_BOOKS}
        book_names = [_BOOK_ID_TO_NAME.get(b, b) for b in detected_books]
        books_html = f"{', '.join(book_names)}"
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
        return [], None, "검색어를 입력하세요"

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
            return [], None, f"결과 없음 (검색어: {query})"

        # Format candidates for UI display
        results = []
        citations = getattr(response, "citations", None)
        for i, candidate in enumerate(response.top_k_results):
            citation = citations[i] if citations else None
            formatted = _format_candidate(candidate, response.parsed_query, citation=citation)
            results.append(formatted)

        return results, response, f"검색 완료 ({len(results)}개 결과)"

    except FileNotFoundError as e:
        return [], None, f"에러: 자료를 찾을 수 없습니다 — {str(e)}"
    except Exception as e:
        return [], None, f"에러: 검색 실행 중 오류 발생 — {str(e)}"


def _format_candidate(candidate: RankedCandidate, parsed_query, *, citation: Optional[Citation] = None) -> dict:
    """
    Map a production RankedCandidate to UI display format.

    Transforms core/retrieval.py data models into the dictionary format
    expected by search_results_table() component.

    When citation is provided and has values, adds author/source_title/
    evidence_confidence keys (additive only — never overwrites existing keys).
    Missing values are omitted entirely (never filled with '' or '-').
    """
    # Build verse reference string from metadata
    # [DBMA-UX-004] book_id는 원시 코드(예: "ROM")라 한글 성경 이름으로
    # 변환해 표시한다 — 그대로 노출하면 사용자에게 의미가 없다.
    vm = candidate.metadata.get("verse_mapping", {})
    if vm and vm.get("book_id"):
        from core.sermon.bible_books import BIBLE_BOOKS
        _book_name = {book_id: name for name, book_id in BIBLE_BOOKS}.get(
            vm["book_id"], vm["book_id"]
        )
        chapter = vm.get("chapter", "?")
        v_start = vm.get("verse_start", "?")
        v_end = vm.get("verse_end", v_start)
        verse_ref = f"{_book_name} {chapter}:{v_start}"
        if v_end and v_end != v_start:
            verse_ref += f"-{v_end}"
    else:
        verse_ref = "본문 참조 없음"

    # Build title from reference + content preview
    content_preview = candidate.content[:120].replace("\n", " ")
    title = f"{verse_ref} — {content_preview}..."

    # Get source file from metadata
    source_file = candidate.metadata.get("source_file", "Unknown source")

    result: dict[str, Any] = {
        "title": title,
        "score": candidate.final_score,
        "type": "설교 자료",
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

    # Add citation fields additively — only when present and non-None
    if citation is not None:
        if citation.source_author:
            result["author"] = citation.source_author
        if citation.source_title:
            result["source_title"] = citation.source_title
        if citation.evidence_confidence is not None:
            result["evidence_confidence"] = citation.evidence_confidence

    return result


# ── Detail Panel Layout ────────────────────────────────────────

def _render_research_page_with_detail() -> None:
    """3영역 레이아웃: 본문(좌주) + 연구 영역(우측) + 행동 영역(하단 3버튼).

    UX-007 §5 Reading Specification — Task Order 048.
    """
    import datetime
    from core.document_detail import get_document_detail
    from ui.components.detail_panel import render_detail_panel

    detail_selection = st.session_state.get("research_detail_selection")
    if detail_selection is None:
        return

    source_file = detail_selection["source_file"]
    document_id = detail_selection["document_id"]
    query_terms = detail_selection.get("query_terms", [])

    # ── Typography CSS for body text ──────────────────────────────
    st.markdown(
        "<style>"
        ".dbma-body-text {"
        "  font-family: 'Source Serif 4', serif;"
        "  font-size: 17px;"
        "  max-width: 640px;"
        "  line-height: 1.85;"
        "}"
        "</style>",
        unsafe_allow_html=True,
    )

    # ── Top row: body (left) + research area (right) ────────────
    cols = st.columns([2, 1])

    # === LEFT: Document body ===
    with cols[0]:
        # Close button (top-left of body area)
        if st.button("닫기", key="research_detail_close_btn", type="primary"):
            st.session_state["research_detail_selection"] = None
            st.rerun()

        # Fetch and render document detail
        detail = get_document_detail(
            source_file=source_file,
            document_id=document_id,
            query_terms=query_terms,
        )

        if not detail.error:
            from core.reading_session import save_last_read
            save_last_read(document_id, detail.title or "", source_file)

        # Wrap render_detail_panel output in typography container
        st.markdown('<div class="dbma-body-text">', unsafe_allow_html=True)
        render_detail_panel(detail, query_terms)
        st.markdown('</div>', unsafe_allow_html=True)

    # === RIGHT: Research area ===
    with cols[1]:
        st.subheader("연구 영역")

        # --- Related docs ---
        st.markdown("**관련 자료**")
        related_results = _fetch_related_docs(query_terms, document_id)
        for i, rd in enumerate(related_results):
            render_citation_card(
                source_file=rd.get("source_file", ""),
                text_location=None,
                doc_type=None,
                author=rd.get("author") or None,
                citation_title=rd.get("source_title") or None,
                relevance_score=rd.get("score", 0.0),
                on_view_original=True,
                key_suffix=f"related_{i}",
            )
            src = rd.get("source_file", "")
            did = rd.get("document_id", "")
            if src or did:
                rkey = f"rel_nav_{i}_{abs(hash(src + did)) & 0xFFFFFFFF:x}"
                if st.button(f"📄 {src}", key=rkey, use_container_width=True):
                    st.session_state["research_detail_selection"] = {
                        "source_file": src,
                        "document_id": did,
                        "query_terms": query_terms,
                    }
                    st.rerun()

        st.divider()

        # --- Follow-up question ---
        st.markdown("**이어서 질문**")
        q_key = f"followup_q_{abs(hash(document_id)) & 0xFFFFFFFF:x}"
        a_key = f"followup_a_{abs(hash(document_id)) & 0xFFFFFFFF:x}"
        if st.text_input("질문 입력", key=q_key, placeholder="현재 문맥에서 질문하세요"):
            user_question = st.session_state[q_key]
            try:
                answer_text, _ = generate_answer(
                    user_question,
                    conversation_history="",
                    file_scope=[source_file],
                )
                st.session_state[a_key] = answer_text if answer_text else "답변을 생성하지 못했습니다."
            except Exception as e:
                logger.warning("Follow-up question failed: %s", e)
                st.session_state[a_key] = "답변 생성 중 오류가 발생했습니다."
        if a_key in st.session_state and st.session_state[a_key]:
            st.markdown(st.session_state[a_key])

    # ── Bottom row: 3 action buttons ─────────────────────────────
    st.divider()
    _render_detail_action_buttons(detail, source_file, document_id)


def _fetch_related_docs(query_terms: list[str], exclude_document_id: str) -> list[dict]:
    """query_terms로 검색하되 exclude_document_id와 일치하는 문서는 제외."""
    if not query_terms:
        return []
    query = " ".join(query_terms)
    results, _, _ = _execute_research_query(query, top_k=10)
    return [r for r in results if r.get("document_id", "") != exclude_document_id]


def _render_detail_action_buttons(
    detail: Any, source_file: str, document_id: str
) -> None:
    """하단 행동 영역: 인용하기 / 연구에 추가 / 설교 연구로 보내기."""
    btn_cols = st.columns(3)

    # 1. 인용하기
    with btn_cols[0]:
        cite_key = f"cite_{abs(hash(document_id)) & 0xFFFFFFFF:x}"
        cite_text_key = f"{cite_key}_text"
        if st.button("인용하기", key=cite_key, use_container_width=True):
            citation_text = _build_citation_text(detail, source_file, document_id)
            st.session_state[cite_text_key] = citation_text
        if st.session_state.get(cite_text_key):
            st.code(st.session_state[cite_text_key], language=None)

    # 2. 연구에 추가
    with btn_cols[1]:
        add_key = f"add_to_res_{abs(hash(document_id)) & 0xFFFFFFFF:x}"
        if st.button("연구에 추가", key=add_key, use_container_width=True):
            _add_to_research_session(detail, source_file, document_id)
            st.toast("연구 세션에 추가되었습니다")

    # 3. 설교 연구로 보내기
    with btn_cols[2]:
        sermon_key = f"send_sermon_{abs(hash(document_id)) & 0xFFFFFFFF:x}"
        if st.button("설교 연구로 보내기", key=sermon_key, use_container_width=True):
            _send_to_sermon_research(source_file, document_id, detail)
            st.toast("설교 연구에 추가되었습니다")


def _build_citation_text(detail: Any, source_file: str, document_id: str) -> str:
    """문서의 출처/저자/위치 정보를 텍스트로 구성."""
    parts = []
    if detail and detail.title:
        parts.append(f"제목: {detail.title}")
    if detail and detail.author:
        parts.append(f"저자: {detail.author}")
    if source_file:
        parts.append(f"출처: {source_file}")
    if document_id:
        parts.append(f"문서 ID: {document_id}")
    if detail and detail.document_type:
        parts.append(f"유형: {detail.document_type}")
    if detail and detail.created_at:
        parts.append(f"생성일: {detail.created_at}")
    return "\n".join(parts)


def _add_to_research_session(detail: Any, source_file: str, document_id: str) -> None:
    """현재 문서를 현재 연구 세션에 참조로 추가."""
    session_id = st.session_state.get("research_session_id", "")
    if not session_id:
        return
    resp_pkg = {
        "top_k_results": [
            {
                "document_id": document_id,
                "source_file": source_file,
                "title": detail.title if detail else "",
                "author": detail.author if detail else "",
                "score": 1.0,
            }
        ],
        "citations": [],
    }
    add_query_result(session_id, "", resp_pkg)


def _send_to_sermon_research(
    source_file: str, document_id: str, detail: Any
) -> None:
    """sermon_research_selection 버퍼에 현재 문서 추가 (Task Order 042 패턴)."""
    st.session_state.setdefault("sermon_research_selection", [])
    st.session_state["sermon_research_selection"].append({
        "tsu_id": document_id,
        "document_id": document_id,
        "excerpt": (detail.full_text[:300] if (detail and detail.full_text) else ""),
        "source_label": source_file,
        "added_at": datetime.datetime.now().isoformat(timespec="seconds"),
    })