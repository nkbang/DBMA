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

import streamlit as st

from ui.pages._base import BasePage
from core.retrieval import QueryProcessor, RankedCandidate
from core.generation import GenerationService
from ui.state.query_processor import get_shared_query_processor


def render_chat_page() -> None:
    """Render the DBMA RAG Chat page."""
    page = BasePage(title="RAG Chat", icon="💬")
    page.render_header()

    _init_chat_state()
    _render_chat_history()

    prompt = st.chat_input("질문을 입력하세요…")
    if prompt:
        _handle_user_message(prompt.strip())
        st.rerun()

    page.render_footer()


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
    """
    st.session_state["chat_messages"].append({"role": "user", "content": question})

    processor = _get_processor()
    generator = _get_generation_service()

    try:
        response = processor.process(question, query_id="chat-ui", k=5)
    except Exception as e:
        st.session_state["chat_messages"].append({
            "role": "assistant",
            "content": f"[검색 실패] {e}",
            "sources": [],
        })
        return

    result = generator.generate(response)

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
