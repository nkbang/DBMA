"""DBMA Design System — RAG Chat Page.

Single-turn question/answer interface connecting the production Retrieval
(core/retrieval.py::QueryProcessor) and Generation (core/generation.py::
GenerationService) boundary to the UI.

Scope (SPRINT17-Phase5-M1b-2):
  - No multi-turn LLM memory — each question is answered independently;
    chat_messages only stores display history, it is not fed back into
    QueryProcessor/GenerationService as conversational context.
  - No citation architecture changes — sources are shown using the same
    RankedCandidate fields ui/pages/research.py already displays.
"""

from typing import Optional

import streamlit as st

from ui.pages._base import BasePage
from core.retrieval import QueryProcessor, RankedCandidate
from core.generation import GenerationService
from ui.state.query_processor import get_shared_query_processor

# 스코프별 반환 청크 수(k) — 좁은 스코프일수록 LLM에 넘기는 컨텍스트가
# 짧아져 응답이 빨라진다(정확도 트레이드오프가 아니라 컨텍스트 길이 문제).
_SCOPE_K = {"단일 파일": 3, "다중 파일": 5, "전체 파일": 5}


def render_chat_page() -> None:
    """Render the DBMA RAG Chat page."""
    page = BasePage(title="RAG Chat", icon="💬")
    page.render_header()

    _init_chat_state()
    _render_scope_selector()
    _render_chat_history()

    prompt = st.chat_input("질문을 입력하세요…")
    if prompt:
        _handle_user_message(prompt.strip())

    page.render_footer()


def _render_scope_selector() -> None:
    """검색 범위 선택 — 단일/다중 파일로 좁히면 그만큼 k(반환 청크 수)가
    줄어 LLM 컨텍스트가 짧아지고 응답이 빨라진다."""
    with st.expander("🔎 검색 범위", expanded=False):
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


def _current_scope() -> tuple[Optional[list[str]], int]:
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
        st.session_state["chat_messages"] = []


def _get_processor() -> QueryProcessor:
    # [SPRINT17-Phase5-M1b-2.1] Shared across all pages that need a
    # QueryProcessor (Research, Chat) — one RetrievalEngine instance per
    # session instead of one per page. [SPRINT21-G Gap#1] recreated
    # automatically when the TSU dataset on disk changes — see
    # ui/state/query_processor.py.
    return get_shared_query_processor()


def _get_generation_service() -> GenerationService:
    if "chat_generation_service" not in st.session_state:
        st.session_state["chat_generation_service"] = GenerationService()
    return st.session_state["chat_generation_service"]


def _handle_user_message(question: str) -> None:
    """Run one retrieval→generation round for a single question.

    No conversational memory: each call parses `question` on its own —
    prior chat_messages are display history only, never passed back into
    QueryProcessor.process() or GenerationService.generate().

    Renders the user message and the streamed assistant answer inline
    (before they're appended to chat_messages) so the LLM response shows
    up token-by-token instead of blocking until the full ~70B-model
    generation finishes.
    """
    st.session_state["chat_messages"].append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    processor = _get_processor()
    generator = _get_generation_service()
    file_scope, k = _current_scope()

    try:
        response = processor.process(question, query_id="chat-ui", k=k, file_scope=file_scope)
    except Exception as e:
        error_msg = f"[검색 실패] {e}"
        with st.chat_message("assistant"):
            st.markdown(error_msg)
        st.session_state["chat_messages"].append({
            "role": "assistant",
            "content": error_msg,
            "sources": [],
        })
        return

    with st.chat_message("assistant"):
        stream = generator.generate_stream(response)
        st.write_stream(stream)
        result = stream.to_result()
        if response.top_k_results:
            with st.expander(f"출처 ({len(response.top_k_results)}개)", expanded=False):
                for candidate in response.top_k_results:
                    _render_source(candidate)

    st.session_state["chat_messages"].append({
        "role": "assistant",
        "content": result.answer,
        "sources": response.top_k_results,
        "error": result.error,
    })


def _render_chat_history() -> None:
    for msg in st.session_state["chat_messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and msg.get("sources"):
                with st.expander(f"출처 ({len(msg['sources'])}개)", expanded=False):
                    for candidate in msg["sources"]:
                        _render_source(candidate)


def _render_source(candidate: RankedCandidate) -> None:
    source_file = candidate.metadata.get("source_file", "Unknown source")
    st.markdown(f"**{source_file}** · score={candidate.final_score:.3f}")
    st.caption(candidate.content[:240].replace("\n", " "))
