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
from core.retrieval import QueryProcessor, RankedCandidate
from core.generation import GenerationService
from core.claim_guard import ClaimGuardResult, RiskLevel
from ui.state.query_processor import get_shared_query_processor, record_query_latency

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
    ClaimGuardResult 같은 객체를 dict로 풀어낸다. 원본 리스트는 건드리지
    않는다(session_state 내용을 그대로 두고 저장용 사본만 만듦)."""
    out = []
    for msg in messages:
        m = dict(msg)
        sources = m.get("sources")
        if sources:
            m["sources"] = [
                s.to_dict() if hasattr(s, "to_dict") else s for s in sources
            ]
        claim_guard_result = m.get("claim_guard_result")
        if claim_guard_result is not None:
            m["claim_guard_result"] = dataclasses.asdict(claim_guard_result)
        out.append(m)
    return out


def _deserialize_messages(raw: list[dict]) -> list[dict]:
    """_serialize_messages()의 역변환 - 저장된 dict를 RankedCandidate/
    ClaimGuardResult 객체로 복원한다. 필드가 안 맞는 등 손상된 레코드는
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
        error_msg = f"[검색 실패] {e}"
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
        stream = generator.generate_stream(response, conversation_history=conversation_history)
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
                for _src_idx, candidate in enumerate(response.top_k_results):
                    _render_source(candidate, _turn_msg_idx, _src_idx)

    st.session_state["chat_messages"].append({
        "role": "assistant",
        "content": result.answer,
        "sources": response.top_k_results,
        "error": result.error,
        "low_confidence": low_confidence,
        "claim_guard_result": claim_guard_result,
    })
    _save_chat_history()


def _is_low_confidence(top_k_results: list) -> bool:
    """See _LOW_CONFIDENCE_SCORE_THRESHOLD docstring above - soft signal
    only, no retrieval/generation behavior changes here."""
    if not top_k_results:
        return True
    return top_k_results[0].final_score < _LOW_CONFIDENCE_SCORE_THRESHOLD


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
    """
    source_file = candidate.metadata.get("source_file", "Unknown source")
    document_id = candidate.metadata.get("document_id", "")

    _render_clickable_source(candidate, source_file, document_id, msg_index, source_index_in_msg)


def _render_clickable_source(
    candidate: RankedCandidate,
    source_file: str,
    document_id: str,
    msg_index: int,
    source_index_in_msg: int,
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

    # Score 표시 (살아있는 기능 — 유지)
    score = getattr(candidate, "final_score", 0.0)
    st.caption(f"신뢰도: {score:.4f}")


