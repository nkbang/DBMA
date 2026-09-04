"""DBMA Design System - RAG Chat Page.

Question/answer interface connecting the production Retrieval
(core/retrieval.py::QueryProcessor) and Generation (core/generation.py::
GenerationService) boundary to the UI.

Scope (SPRINT17-Phase5-M1b-2):
  - No citation architecture changes - sources are shown using the same
    RankedCandidate fields ui/pages/research.py already displays.

Session-scoped continuity ("Plan B", 2026-07-24): the RETRIEVAL query is
still independent per turn - QueryProcessor.process(question) never sees
prior turns, so search itself is not widened or rewritten by conversation
history (that would be "Plan A", query rewriting/condensation - a larger,
not-yet-implemented change). What IS session-scoped: _build_conversation_
history() feeds the last _HISTORY_MAX_TURNS exchanges into the ANSWER-
GENERATION prompt only (GenerationService._build_prompt's conversation_
history param), so follow-up questions read naturally within one browser
session.

Cross-refresh persistence (2026-07-30): Streamlit resets session_state
on a hard page refresh (new session) - this is framework behavior, not a
regression. Since DBMA is a local single-user app, chat_messages is now
mirrored to disk (_CHAT_HISTORY_FILE) after every turn and restored by
_init_chat_state() on a fresh session, so a refresh no longer loses the
conversation. Use the "대화 초기화" button (_clear_chat_history) to
start a new topic - there's still no automatic topic-boundary detection.
"""

import dataclasses
import json
import logging
import os
from pathlib import Path
from typing import Optional

import streamlit as st

from ui.pages._base import BasePage
from core.config import DATA_DIR
from core.retrieval import QueryProcessor, RankedCandidate, Citation
from core.generation import GenerationService
from core.claim_guard import ClaimGuardResult, RiskLevel
from ui.state.query_processor import get_shared_query_processor, record_query_latency
from ui.components.citation_card import render_citation_card
from NAE.smith_activation import should_activate_smith, rewrite_query_for_smith

logger = logging.getLogger(__name__)

# [2026-07-30] 새로고침(F5) 시 chat_messages가 초기화되는 문제 - Streamlit의
# session_state는 브라우저 세션에 묶여 있어 새로고침하면 새 세션으로 취급된다
# (프레임워크 자체 동작, 회귀 아님). DBMA는 로컬 단일 사용자 앱이므로 디스크에
# 마지막 대화를 저장했다가 새 세션 시작 시 복원하는 방식으로 해결한다.
_CHAT_HISTORY_FILE = os.path.join(DATA_DIR, "chat_session_history.json")

# 스코프별 반환 청크 수(k) - 좁은 스코프일수록 LLM에 넘기는 컨텍스트가
# 짧아져 응답이 빨라진다(정확도 트레이드오프가 아니라 컨텍스트 길이 문제).
_SCOPE_K = {"단일 파일": 3, "다중 파일": 5, "전체 파일": 5}

# [2026-07-24, "Plan B" 세션 내 연속성] 최근 몇 턴(사용자+어시스턴트 쌍)까지
# 답변 생성 프롬프트에 포함할지 - 검색 쿼리(response.question)는 여전히
# 마지막 질문 그대로다(재작성 없음). 세션이 바뀌면 chat_messages가 빈
# 리스트로 리셋되므로 "세션이 남아있으면 이어지고, 바뀌면 새 주제"가
# 자연스럽게 성립한다.
_HISTORY_MAX_TURNS = 3
_HISTORY_MAX_CHARS_PER_MESSAGE = 300

# [2026-07-24, soft relevance warning] RetrievalEngine has no relevance
# floor - it always returns top-k candidates regardless of whether any of
# them actually address the question (confirmed by reproduction: an
# unrelated query like "오늘 서울 날씨 어때?" still returned 5 "results"
# scoring 0.37~0.41, one of which was an unrelated illustration paragraph
# that happened to contain the word "rain"). This constant is a **soft,
# provisional** floor calibrated from only 4 sample queries (relevant:
# 0.46~0.51, irrelevant: 0.37~0.41) - NOT a rigorously validated
# threshold. It only adds a caption warning; it never blocks or alters the
# generated answer (see feedback_avoid_risky_uncertain_design: don't gate
# behavior on an under-validated signal). Revisit with a larger labeled
# sample before tightening this into anything stronger.
_LOW_CONFIDENCE_SCORE_THRESHOLD = 0.45


def render_chat_page() -> None:
    """Render the DBMA RAG Chat page."""
    page = BasePage(title="질문하기", icon="💬")
    page.render_header()

    _init_chat_state()

    detail_selection = st.session_state.get("chat_detail_selection")
    if detail_selection is not None:
        _render_chat_page_with_detail()
    else:
        _render_scope_selector()
        _render_chat_history()

    prompt = st.chat_input("질문을 입력하세요...")
    if prompt:
        _handle_user_message(prompt.strip())

    page.render_footer()


def _render_scope_selector() -> None:
    """검색 범위 선택 - 단일/다중 파일로 좁히면 그만큼 k(반환 청크 수)가
    줄어 LLM 컨텍스트가 짧아지고 응답이 빨라진다."""
    with st.expander("검색 범위", expanded=False):
        st.radio(
            "검색 범위",
            options=["전체 파일", "다중 파일", "단일 파일"],
            horizontal=True,
            key="chat_scope_mode",
            label_visibility="collapsed",
        )
        mode = st.session_state.get("chat_scope_mode", "전체 파일")
        if mode in ("단일 파일", "다중 파일"):
            files = _get_processor().engine.list_source_files()
            if mode == "단일 파일":
                st.selectbox("파일 선택", options=files, key="chat_scope_single")
            else:
                st.multiselect("파일 선택 (복수)", options=files, key="chat_scope_multi")
        if st.button("대화 초기화", key="chat_clear_history"):
            _clear_chat_history()
            st.rerun()


def _current_scope() -> tuple:
    """Returns (file_scope, k) for the currently selected search scope."""
    mode = st.session_state.get("chat_scope_mode", "전체 파일")
    k = _SCOPE_K.get(mode, 5)
    if mode == "단일 파일":
        selected = st.session_state.get("chat_scope_single")
        return ([selected] if selected else None), k
    if mode == "다중 파일":
        selected = st.session_state.get("chat_scope_multi") or []
        return (selected or None), k
    return None, k


def _init_chat_state() -> None:
    if "chat_messages" not in st.session_state:
        st.session_state["chat_messages"] = _load_chat_history()


def _serialize_messages(messages: list[dict]) -> list[dict]:
    """chat_messages를 JSON 저장 가능한 형태로 변환 - RankedCandidate/
    ClaimGuardResult/Citation 같은 객체를 dict로 풀어낸다. 원본 리스트는 건드리지
    않는다(session_state 내용을 그대로 두고 저장용 사본만 만듦)."""
    out = []
    for msg in messages:
        m = dict(msg)
        sources = m.get("sources")
        if sources:
            m["sources"] = [
                s.to_dict() if hasattr(s, "to_dict") else s for s in sources
            ]
        citations = m.get("citations")
        if citations:
            m["citations"] = [
                dataclasses.asdict(c) if hasattr(c, "__dataclass_fields__") else c
                for c in citations
            ]
        claim_guard_result = m.get("claim_guard_result")
        if claim_guard_result is not None:
            m["claim_guard_result"] = dataclasses.asdict(claim_guard_result)
        out.append(m)
    return out


def _deserialize_messages(raw: list[dict]) -> list[dict]:
    """_serialize_messages()의 역변환 - 저장된 dict를 RankedCandidate/
    ClaimGuardResult/Citation 객체로 복원한다. 필드가 안 맞는 등 손상된 레코드는
    건너뛴다(저장 파일이 낡은 스키마여도 채팅 자체는 죽지 않게)."""
    out = []
    for msg in raw:
        m = dict(msg)
        sources = m.get("sources")
        if sources:
            restored = []
            for s in sources:
                try:
                    restored.append(RankedCandidate(**s))
                except TypeError:
                    continue
            m["sources"] = restored
        citations = m.get("citations")
        if citations:
            restored_citations = []
            for c in citations:
                try:
                    restored_citations.append(Citation(**c))
                except (TypeError, KeyError):
                    continue
            m["citations"] = restored_citations
        claim_guard_result = m.get("claim_guard_result")
        if claim_guard_result is not None:
            try:
                cg = dict(claim_guard_result)
                cg["risk_level"] = RiskLevel(cg["risk_level"])
                m["claim_guard_result"] = ClaimGuardResult(**cg)
            except (TypeError, ValueError, KeyError):
                m["claim_guard_result"] = None
        out.append(m)
    return out


def _save_chat_history() -> None:
    """현재 chat_messages를 디스크에 저장 - 실패해도 채팅 자체는 계속
    동작해야 하므로 예외를 삼키고 경고 로그만 남긴다(부가 기능 장애가
    핵심 기능을 막지 않게, Sprint D ClaimGuard 통합과 같은 원칙)."""
    try:
        os.makedirs(os.path.dirname(_CHAT_HISTORY_FILE), exist_ok=True)
        serialized = _serialize_messages(st.session_state.get("chat_messages", []))
        with open(_CHAT_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(serialized, f, ensure_ascii=False)
    except Exception as e:
        logger.warning("[chat] 대화 기록 저장 실패: %s", e)


def _load_chat_history() -> list[dict]:
    """디스크에 저장된 마지막 대화를 복원. 파일이 없거나 손상됐으면 빈
    대화로 시작한다 - 저장된 형식을 추측해서 복구하지 않는다."""
    if not os.path.exists(_CHAT_HISTORY_FILE):
        return []
    try:
        with open(_CHAT_HISTORY_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
        return _deserialize_messages(raw)
    except Exception as e:
        logger.warning("[chat] 대화 기록 복원 실패, 빈 대화로 시작: %s", e)
        return []


def _clear_chat_history() -> None:
    st.session_state["chat_messages"] = []
    try:
        if os.path.exists(_CHAT_HISTORY_FILE):
            os.remove(_CHAT_HISTORY_FILE)
    except OSError as e:
        logger.warning("[chat] 대화 기록 파일 삭제 실패: %s", e)


def _build_conversation_history() -> str:
    """Last _HISTORY_MAX_TURNS exchanges as plain text for the generation
    prompt (see GenerationService._build_prompt's conversation_history
    param). Must be called BEFORE the current question is appended to
    chat_messages, so it reflects prior turns only."""
    messages = st.session_state.get("chat_messages", [])
    recent = messages[-(_HISTORY_MAX_TURNS * 2):]
    lines = []
    for msg in recent:
        role_label = "사용자" if msg["role"] == "user" else "어시스턴트"
        content = msg["content"][:_HISTORY_MAX_CHARS_PER_MESSAGE]
        lines.append(f"{role_label}: {content}")
    return "\n".join(lines)


def _get_processor() -> QueryProcessor:
    # [SPRINT17-Phase5-M1b-2.1] Shared across all pages that need a
    # QueryProcessor (Research, Chat) - one RetrievalEngine instance per
    # session instead of one per page. [SPRINT21-G Gap#1] recreated
    # automatically when the TSU dataset on disk changes - see
    # ui/state/query_processor.py.
    return get_shared_query_processor()


def _get_generation_service() -> GenerationService:
    if "chat_generation_service" not in st.session_state:
        st.session_state["chat_generation_service"] = GenerationService()
    return st.session_state["chat_generation_service"]


def _settings_overrides() -> dict:
    """Sidebar 설정(ui/app.py::_render_settings_expander)에서 고른 값만
    generate_stream()에 넘긴다 — 고른 적이 없으면 빈 dict이라 core의
    DEFAULT_GEN_MODEL/DEFAULT_TEMPERATURE 기본값이 그대로 쓰인다.

    ui.app을 import하지 않고 session_state 키를 직접 읽는다: ui/app.py가
    ui.pages.chat을 import하므로 반대 방향 import는 순환이 된다.
    """
    overrides: dict = {}
    gen_model = st.session_state.get("settings_gen_model")
    if gen_model:
        overrides["gen_model"] = gen_model
    temperature = st.session_state.get("settings_temperature")
    if temperature is not None:
        overrides["temperature"] = float(temperature)
    return overrides


def _format_smith_context(smith_results: list[dict]) -> str:
    """Format Smith Bible Dictionary results as a distinct context block.

    Results are separated from TSU context with a clear delimiter so the LLM
    knows these are background reference entries, not scripture passages.

    Args:
        smith_results: Raw results from search_reference() for Smith entries.

    Returns:
        Formatted string block, or empty string if no results.
    """
    if not smith_results:
        return ""

    lines = ["<reference>", "[참고 자료: Smith Bible Dictionary]", ""]
    for i, entry in enumerate(smith_results, 1):
        heading = entry.get("heading_context", "") or entry.get("text", "")[:80]
        volume = entry.get("volume", "")
        page = entry.get("page_start")
        page_info = ""
        if volume and page:
            page_info = f" (Vol. {volume}, p.{page})"
        elif page:
            page_info = f" (p.{page})"

        text = entry.get("text", "")
        lines.append(f"[{i}] {heading}{page_info}")
        lines.append(text)
        lines.append("")

    lines.append("</reference>")
    return "\n".join(lines)


def _inject_smith_context(
    response: "ResponsePackage",
    query: str,
) -> list[dict]:
    """Check Smith activation and inject context into the response.

    This is a side-effect function that mutates `response.llm_context_block`
    in-place to append Smith results. It also returns Smith results for
    potential display in the UI.

    Args:
        response: The ResponsePackage from TSU retrieval.
        query: The original user question.

    Returns:
        Smith results list (may be empty if not activated or no results).
    """
    # Check if Smith should be activated for this query
    if not should_activate_smith(query):
        return []

    # Rewrite query for better Smith search
    search_query = rewrite_query_for_smith(query) or query

    # Search Smith reference corpus (fault-isolated — never raises)
    try:
        from NAE.reference_retrieval_adapter import search_reference
        smith_results = search_reference(search_query, top_k=3)
    except Exception as e:
        logger.warning("[chat] Smith retrieval failed (TSU unaffected): %s", e)
        return []

    # Filter to only Smith Bible Dictionary entries
    smith_entries = [
        r for r in smith_results
        if "smith" in str(r.get("source_id", "")).lower()
        or "smith" in str(r.get("volume", "")).lower()
    ]

    if not smith_entries:
        return []

    # Format Smith context block
    smith_context = _format_smith_context(smith_entries)

    # ADR-028 §8/§5: hierarchy instruction inserted exactly once, between
    # TSU evidence and the <reference> block — Smith must never be read as
    # primary evidence or override TSU theological corpus / scripture.
    hierarchy_notice = (
        "참고: 아래 <reference> 항목은 보조 자료(Smith Bible Dictionary)입니다. "
        "주요 근거는 위 신학 문헌(TSU) 및 성경 본문을 우선하고, "
        "이 참고 자료가 그 해석을 대체하거나 덮어쓰지 않도록 하십시오."
    )
    smith_block = f"{hierarchy_notice}\n\n{smith_context}"

    # Append to existing TSU context (if any) — distinct section
    if response.llm_context_block:
        response.llm_context_block += f"\n\n{smith_block}"
    else:
        response.llm_context_block = smith_block

    logger.info(
        "[chat] Smith Bible Dictionary activated for query=%r → %d entries injected",
        query[:50], len(smith_entries),
    )
    return smith_entries


def generate_answer(
    question: str,
    *,
    conversation_history: str | None = None,
    k: int = 5,
    file_scope: list[str] | None = None,
) -> tuple[str, list[RankedCandidate]]:
    """Run retrieval + generation for a single question.

    Pure-ish function: returns (answer_text, sources) without depending on
    chat_messages session state or rendering anything.  Designed to be
    imported by research.py so both pages share the same GenerationService
    call path.

    SPRINT34-SMITH-PHASEB: Smith Bible Dictionary context is now injected
    between TSU retrieval and generation when query intent matches dictionary-
    style lookups (proper nouns, theological terms, definition-seeking).

    Parameters
    ----------
    question : str
        The user's query/question.
    conversation_history : str, optional
        Prior conversation text for the generation prompt.  None means
        no history (used by research.py).
    k : int
        Number of retrieval results to return.
    file_scope : list[str] | None
        Optional file scope for retrieval.

    Returns
    -------
    tuple[str, list[RankedCandidate]]
        (answer_text, sources) — answer_text may be empty on generation
        failure; sources is always a list (possibly empty).
    """
    processor = _get_processor()
    generator = _get_generation_service()

    try:
        response = processor.process(question, query_id="shared-gen", k=k, file_scope=file_scope)
    except Exception as e:
        logger.warning("Retrieval failed in generate_answer: %s", e)
        return ("", [])

    # SPRINT34-SMITH-PHASEB: Inject Smith Bible Dictionary context
    # between TSU retrieval and generation — fault-isolated, zero regression.
    smith_results = _inject_smith_context(response, question)

    # Even if retrieval returns no results, try generation (may still produce
    # a useful answer from system prompt / prior context).
    try:
        stream = generator.generate_stream(
            response,
            conversation_history=conversation_history or "",
            **_settings_overrides(),
        )
        for _ in stream:  # consume the lazy generator to fill _answer_parts
            pass
        result = stream.to_result()
        answer_text = result.answer if hasattr(result, "answer") else ""
    except Exception as e:
        logger.warning("Generation failed in generate_answer: %s", e)
        answer_text = ""

    sources = response.top_k_results if response and response.top_k_results else []
    return (answer_text, sources)


def _handle_user_message(question: str) -> None:
    """Run one retrieval-generation round for a single question.

    Retrieval query stays independent per call: question alone is parsed
    by QueryProcessor.process() - prior turns never rewrite or widen the
    search query. [2026-07-24, "Plan B"] The answer-generation prompt now
    additionally receives recent chat_messages (via _build_conversation_
    history(), captured BEFORE this turn's question is appended below) so
    follow-up questions read naturally within a session; this is a smaller
    change than query-rewriting ("Plan A") and was chosen first per that
    design discussion.

    Renders the user message and the streamed assistant answer inline
    (before they're appended to chat_messages) so the LLM response shows
    up token-by-token instead of blocking until the full ~70B-model
    generation finishes.
    """
    conversation_history = _build_conversation_history()

    st.session_state["chat_messages"].append({"role": "user", "content": question})
    _save_chat_history()
    with st.chat_message("user"):
        st.markdown(question)

    processor = _get_processor()
    generator = _get_generation_service()
    file_scope, k = _current_scope()

    try:
        response = processor.process(question, query_id="chat-ui", k=k, file_scope=file_scope)
        record_query_latency(response.performance_metrics.total_ms)
    except Exception as e:
        logger.exception("Chat: retrieval failed")
        error_msg = "검색 중 문제가 있었습니다. 다시 시도해주세요."
        with st.chat_message("assistant"):
            st.markdown(error_msg)
        st.session_state["chat_messages"].append({
            "role": "assistant",
            "content": error_msg,
            "sources": [],
        })
        _save_chat_history()
        return

    low_confidence = _is_low_confidence(response.top_k_results)

    with st.chat_message("assistant"):
        stream = generator.generate_stream(
            response,
            conversation_history=conversation_history,
            **_settings_overrides(),
        )
        st.write_stream(stream)
        result = stream.to_result()
        claim_guard_result = getattr(result, "claim_guard_result", None)
        if low_confidence:
            _render_low_confidence_warning()
        if claim_guard_result and (
            claim_guard_result.absolute_claim_blocked
            or claim_guard_result.scope_qualifier_required
        ):
            _render_claim_guard_warning(claim_guard_result)
        if response.top_k_results:
            # Determine this turn's message index for stable key generation.
            msgs = st.session_state.get("chat_messages", [])
            _turn_msg_idx = len(msgs) - 1  # the assistant message just appended
            with st.expander(f"출처 ({len(response.top_k_results)}개)", expanded=False):
                citations = getattr(response, "citations", None)
                for _src_idx, candidate in enumerate(response.top_k_results):
                    citation = citations[_src_idx] if citations else None
                    _render_source(candidate, _turn_msg_idx, _src_idx, citation=citation)

    st.session_state["chat_messages"].append({
        "role": "assistant",
        "content": result.answer,
        "sources": response.top_k_results,
        "citations": getattr(response, "citations", None),
        "error": result.error,
        "low_confidence": low_confidence,
        "claim_guard_result": claim_guard_result,
    })
    _save_chat_history()


def _is_low_confidence(top_k_results: list) -> bool:
    """Soft confidence signal that adapts to the scoring engine.

    Legacy (weighted-sum) path: uses `final_score` with _LOW_CONFIDENCE_SCORE_THRESHOLD
    (0.45), calibrated for weighted-sum scores in ~0.35~0.52 range.

    Hybrid (RRF) path: RRF scores (~0.04~0.05 scale) cannot serve as confidence
    signals — all relevant and irrelevant queries cluster in the same narrow range.
    Instead, we use `theological_score` (semantic relevance) as the primary signal,
    which better correlates with actual relevance regardless of score scale.

    Detection heuristic: RRF scores are always < 0.1 while legacy weighted-sum
    scores are >= 0.35. This cleanly separates the two paths without schema changes.

    Observed theological_score ranges:
        관련 있음(신학): 0.135~0.315 (BibleIndex boost can also raise confidence)
        관련 없음(일상): 0.135 or lower (top-1 rarely exceeds 0.165)

    Threshold 0.15 on theological_score separates the clusters with margin.
    """
    if not top_k_results:
        return True

    top = top_k_results[0]

    # Detect scoring engine by final_score scale
    is_rrf_path = top.final_score < 0.1

    if is_rrf_path:
        # Hybrid (RRF) path — use theological_score as confidence signal
        theo = top.theological_score
        passage = top.passage_score

        # BibleIndex hit → very specific match, high confidence
        if passage > 0:
            return False

        # Semantic relevance threshold
        if theo >= 0.15:
            return False

        return True
    else:
        # Legacy (weighted-sum) path — unchanged from the original signal
        # (Task Order 050 scope: hybrid path only, legacy path untouched).
        return top.final_score < _LOW_CONFIDENCE_SCORE_THRESHOLD


def _render_low_confidence_warning() -> None:
    st.caption("검색 결과 신뢰도가 낮습니다 - 관련 문서를 찾지 못했을 수 있습니다.")


def _render_claim_guard_warning(result) -> None:
    """ClaimGuard가 위험 주장을 탐지했을 때 안내 박스를 표시한다.
    _render_low_confidence_warning()와 동일한 패턴(st.caption)."""
    if result.suggested_wording:
        st.caption(f"주장 검증: {result.suggested_wording}")
    else:
        st.caption(f"주장 검증: {result.reason}")


def _render_chat_history() -> None:
    msgs = st.session_state.get("chat_messages", [])
    for _msg_idx, msg in enumerate(msgs):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and msg.get("low_confidence"):
                _render_low_confidence_warning()
            if msg["role"] == "assistant" and msg.get("claim_guard_result"):
                _render_claim_guard_warning(msg["claim_guard_result"])
            if msg["role"] == "assistant" and msg.get("sources"):
                with st.expander(f"출처 ({len(msg['sources'])}개)", expanded=False):
                    for _src_idx, candidate in enumerate(msg["sources"]):
                        _render_source(candidate, _msg_idx, _src_idx)


def _render_chat_page_with_detail() -> None:
    """2단 레이아웃: 왼쪽 채팅/검색, 오른쪽 문서 상세 패널."""
    from core.document_detail import get_document_detail
    from ui.components.detail_panel import render_detail_panel

    cols = st.columns([2, 1])
    with cols[0]:
        _render_scope_selector()
        _render_chat_history()

    detail_selection = st.session_state.get("chat_detail_selection")
    if detail_selection is None:
        return

    source_file = detail_selection["source_file"]
    document_id = detail_selection["document_id"]
    query_terms = detail_selection.get("query_terms", [])

    with cols[1]:
        # 닫기 버튼
        if st.button("닫기", key="chat_detail_close_btn", type="primary"):
            st.session_state["chat_detail_selection"] = None
            st.rerun()

        st.divider()

        # 문서 상세 정보 로드
        detail = get_document_detail(
            source_file=source_file,
            document_id=document_id,
            query_terms=query_terms,
        )

        if not detail.error:
            from core.reading_session import save_last_read
            save_last_read(document_id, detail.title or "", source_file)

        # 상세 패널 렌더링
        render_detail_panel(detail, query_terms)


def _escape_for_html(text: str) -> str:
    """HTML special characters to safe entities."""
    result = text.replace(chr(38), chr(38) + "amp;")
    result = result.replace(chr(60), chr(38) + "lt;")
    result = result.replace(chr(62), chr(38) + "gt;")
    return result


def _render_source(
    candidate: RankedCandidate,
    msg_index: int,
    source_index_in_msg: int,
    citation: Optional[Citation] = None,
) -> None:
    """출처를 표시하고, 헤드라인을 클릭하면 우측에 문서 상세 패널을 연다.

    Parameters
    ----------
    candidate : RankedCandidate
        출처 청프
    msg_index : int
        chat_messages 리스트에서의 메시지 인덱스 — key 안정성 보장
    source_index_in_msg : int
        해당 메시지 내 sources 리스트에서의 순번 — key 안정성 보장
    citation : Citation, optional
        대응하는 Citation 객체 — author/source_title/evidence_confidence 표시용
    """
    source_file = candidate.metadata.get("source_file", "Unknown source")
    document_id = candidate.metadata.get("document_id", "")

    _render_clickable_source(candidate, source_file, document_id, msg_index, source_index_in_msg, citation=citation)


def _render_clickable_source(
    candidate: RankedCandidate,
    source_file: str,
    document_id: str,
    msg_index: int,
    source_index_in_msg: int,
    citation: Optional[Citation] = None,
) -> None:
    """클릭 가능한 출처 headline을 렌더링한다.

    Widget key is built from msg_index + source_index_in_msg + tsu_id hash.
    This guarantees the same button always gets the same key across reruns,
    because msg_index and source_index_in_msg depend only on rendering position,
    not on any global counter that increments on every rerun.

    Widget key must also be unique per rendering instance to avoid
    StreamlitDuplicateElementKey when the same source appears
    across multiple chat turns or within the same expander.
    """
    # Get heading_path from candidate metadata for display label
    structure = candidate.metadata.get("structure", {})
    heading_path = structure.get("heading_path", [])
    heading_hierarchy = " > ".join(heading_path) if heading_path else ""
    display_label = heading_hierarchy or source_file or "출처 미상"

    # Stable key: depends only on rendering position, not on any counter.
    btn_key = f"nav_src_{msg_index}_{source_index_in_msg}_{abs(hash(candidate.tsu_id)) & 0xFFFFFFFF:x}"

    can_navigate = bool(source_file or document_id)

    if can_navigate:
        # Get the current question (last user message content) for query_terms
        chat_messages = st.session_state.get("chat_messages", [])
        query_terms = []
        # Find the last user message before this assistant message
        for msg in reversed(chat_messages):
            if msg["role"] == "user":
                query_terms = msg["content"].split()
                break

        if st.button(
            f"📄 {display_label}",
            key=btn_key,
            type="primary",
            use_container_width=True,
        ):
            # Set chat_detail_selection to open detail panel on the right
            st.session_state["chat_detail_selection"] = {
                "source_file": source_file,
                "document_id": document_id,
                "query_terms": query_terms,
            }
            st.rerun()
    else:
        # Graceful degradation
        st.caption(f"출처 정보 부족: {display_label}")

    # Citation card per DBMA-UX-007 §6 (replaces raw score exposure)
    score = getattr(candidate, "final_score", 0.0)
    structure = candidate.metadata.get("structure", {})

    # Use heading_path (real field) instead of non-existent text_location
    heading_path = structure.get("heading_path", [])
    text_location = " > ".join(heading_path) if heading_path else None

    doc_type_val = candidate.metadata.get("doc_type") or None

    # Restore author/source info that was lost in v1 (problem 2)
    author_val = citation.source_author if citation else None
    title_val = citation.source_title if citation else None

    citation_key_suffix = f"{msg_index}_{source_index_in_msg}"

    render_citation_card(
        source_file=source_file,
        text_location=text_location,
        doc_type=doc_type_val,
        author=author_val,
        citation_title=title_val,
        relevance_score=score,
        on_view_original=True,
        on_copy_citation=False,
        key_suffix=citation_key_suffix,
    )

    # Connect "원문 다시 보기" button to actual navigation (problem 1)
    # The button key must match the key used in render_citation_card
    btn_key_base = f"cite_btn_{abs(hash(source_file + citation_key_suffix)) & 0xFFFFFFFF:x}"
    view_btn_key = f"{btn_key_base}_view"

    if st.session_state.get(view_btn_key, False):
        # Get the current question for query_terms
        chat_messages = st.session_state.get("chat_messages", [])
        query_terms = []
        for msg in reversed(chat_messages):
            if msg["role"] == "user":
                query_terms = msg["content"].split()
                break

        # Navigate to document detail panel (same logic as the headline button)
        st.session_state["chat_detail_selection"] = {
            "source_file": source_file,
            "document_id": document_id,
            "query_terms": query_terms,
        }
        st.rerun()


