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
session. Streamlit resets chat_messages to [] on a new session, so a new
session already starts a fresh topic - no explicit "topic boundary"
detection was needed for that half of the design.
"""

from pathlib import Path
from typing import Optional

import streamlit as st

from ui.pages._base import BasePage
from core.retrieval import QueryProcessor, RankedCandidate
from core.generation import GenerationService
from ui.state.query_processor import get_shared_query_processor, record_query_latency

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
    page = BasePage(title="RAG Chat", icon="chat")
    page.render_header()

    _init_chat_state()
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
        st.session_state["chat_messages"] = []


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
        return

    low_confidence = _is_low_confidence(response.top_k_results)

    with st.chat_message("assistant"):
        stream = generator.generate_stream(response, conversation_history=conversation_history)
        st.write_stream(stream)
        result = stream.to_result()
        if low_confidence:
            _render_low_confidence_warning()
        if response.top_k_results:
            with st.expander(f"출처 ({len(response.top_k_results)}개)", expanded=False):
                for candidate in response.top_k_results:
                    _render_source(candidate)

    st.session_state["chat_messages"].append({
        "role": "assistant",
        "content": result.answer,
        "sources": response.top_k_results,
        "error": result.error,
        "low_confidence": low_confidence,
    })


def _is_low_confidence(top_k_results: list) -> bool:
    """See _LOW_CONFIDENCE_SCORE_THRESHOLD docstring above - soft signal
    only, no retrieval/generation behavior changes here."""
    if not top_k_results:
        return True
    return top_k_results[0].final_score < _LOW_CONFIDENCE_SCORE_THRESHOLD


def _render_low_confidence_warning() -> None:
    st.caption("검색 결과 신뢰도가 낮습니다 - 관련 문서를 찾지 못했을 수 있습니다.")


def _render_chat_history() -> None:
    for msg in st.session_state["chat_messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and msg.get("low_confidence"):
                _render_low_confidence_warning()
            if msg["role"] == "assistant" and msg.get("sources"):
                with st.expander(f"출처 ({len(msg['sources'])}개)", expanded=False):
                    for candidate in msg["sources"]:
                        _render_source(candidate)


def _escape_for_html(text: str) -> str:
    """HTML special characters to safe entities."""
    result = text.replace(chr(38), chr(38) + "amp;")
    result = result.replace(chr(60), chr(38) + "lt;")
    result = result.replace(chr(62), chr(38) + "gt;")
    return result


def _render_source(candidate: RankedCandidate) -> None:
    """출처를 표시하고, 헤드라인을 클릭하면 원본 내용을 보여주는 모달을 연결한다.

    [DBMA-UI-NAV-001] Headline 클릭 시 Library 문서 상세로 네비게이션 가능.
    """
    from ui.components.source_link import source_link

    source_file = candidate.metadata.get("source_file", "Unknown source")
    structure = candidate.metadata.get("structure", {})
    heading_path = structure.get("heading_path", [])

    # 헤드라인 경로 생성 (상위 -> 하위 순서)
    heading_hierarchy = " > ".join(heading_path) if heading_path else ""

    # 고유 ID 생성 (각 출처마다 고유한 모달 연결용) - hash()는 음수를 반환할 수 있으므로 abs() 사용
    _source_hash = abs(hash(candidate.tsu_id + str(candidate.final_score))) & 0xFFFFFFFF
    source_id = f"source-{_source_hash:x}"

    # DBMA-UI-NAV-001: 클릭 가능한 source link로 교체
    # headline을 버튼으로 표시하고 클릭 시 Library detail + modal 동시 오픈
    _render_clickable_source(candidate, source_file, heading_path, source_id)

    # 원본 내용 모달 (JavaScript 기반) - 기존 유지
    _render_source_modal(source_id, candidate.content, source_file, heading_path)


def _render_clickable_source(
    candidate: RankedCandidate,
    source_file: str,
    heading_path: list,
    source_id: str,
) -> None:
    """[DBMA-UI-NAV-001] 클릭 가능한 출처 headline을 렌더링한다.

    클릭 시:
    1. session state에 source info 저장 (Library detail용)
    2. JS로 원본 모달 열기
    """
    heading_hierarchy = " > ".join(heading_path) if heading_path else ""
    display_label = heading_hierarchy or source_file or "출처 미상"

    # 고유 버튼 키
    btn_key = f"nav_src_{abs(hash(candidate.tsu_id)) & 0xFFFFFFFF:x}"

    can_navigate = bool(source_file or candidate.metadata.get("document_id"))

    if can_navigate:
        if st.button(
            f"📄 {display_label}",
            key=btn_key,
            type="primary",
            use_container_width=True,
        ):
            # 1. Library detail navigation info
            st.session_state["_dbma_source_nav"] = {
                "source_file": source_file,
                "document_id": candidate.metadata.get("document_id", ""),
                "label": display_label,
                "modal_js": f"document.getElementById('{source_id}').classList.add('show');",
            }
            st.rerun()
    else:
        # Graceful degradation
        st.caption(f"출처 정보 부족: {display_label}")

    # Score 표시
    score = getattr(candidate, "final_score", 0.0)
    st.caption(f"신뢰도: {score:.4f}")


def _render_source_modal(source_id: str, content: str, source_file: str, heading_path: list) -> None:
    """원본 내용을 보여주는 JavaScript 모달을 렌더링한다."""
    # heading HTML - heading_path가 없으면 빈 문자열
    if heading_path:
        _heading_html = '<h3 class="modal-heading-' + source_id + '">' + ("> ").join(heading_path) + '</h3>'
    else:
        _heading_html = ""

    # CSS 템플릿 - 포맷팅이 내용을 건드리지 않도록 단순 문자열 결합만 사용
    _CSS_TEMPLATE = (
        "<style>\n"
        ".modal-{sid} {{ display: none; position: fixed; top: 0; left: 0;\n"
        "    width: 100%; height: 100%; background: rgba(0,0,0,0.5);\n"
        "    z-index: 9999; justify-content: center; align-items: center; }}\n"
        ".modal-{sid}.show {{ display: flex; }}\n"
        ".modal-content-{sid} {{ background: white; border-radius: 8px;\n"
        "    padding: 20px; max-width: 80%; max-height: 80%; overflow: auto;\n"
        "    position: relative; box-shadow: 0 4px 16px rgba(0,0,0,0.3); }}\n"
        ".modal-close-{sid} {{ position: absolute; top: 10px; right: 15px;\n"
        "    cursor: pointer; font-size: 24px; color: #666; background: none;\n"
        "    border: none; }}\n"
        ".modal-close-{sid}:hover {{ color: #000; }}\n"
        ".modal-heading-{sid} {{ margin: 0 0 15px 0; padding-bottom: 10px;\n"
        "    border-bottom: 1px solid #eee; color: #333; }}\n"
        ".modal-source-{sid} {{ font-size: 12px; color: #888; margin-bottom: 15px; }}\n"
        ".modal-body-{sid} {{ white-space: pre-wrap; line-height: 1.6;\n"
        "    font-size: 14px; color: #333; }}\n"
        "</style>\n"
    )

    _BODY_TEMPLATE = (
        '<div id="{sid}" class="modal-{sid}">\n'
        '  <div class="modal-content-{sid}" onclick="event.stopPropagation()">\n'
        '    <button class="modal-close-{sid}" '
        "onclick=\"document.getElementById('{sid}').classList.remove('show')\">X</button>\n"
        "  {heading}\n"
        '    <p class="modal-source-{sid}">출처: {src}</p>\n'
        '    <div class="modal-body-{sid}">{body}</div>\n'
        "  </div>\n"
        "</div>\n"
        "<script>\n"
        "document.getElementById('{sid}').addEventListener('click', function(e) {{\n"
        "  if (e.target === this) {{ this.classList.remove('show'); }}\n"
        "}});\n"
        "</script>\n"
    )

    _escaped_body = _escape_for_html(content[:5000]).replace("\n", "<br>")

    css_part = _CSS_TEMPLATE.format(sid=source_id)
    body_part = _BODY_TEMPLATE.format(
        sid=source_id,
        heading=_heading_html,
        src=source_file,
        body=_escaped_body,
    )
    modal_html = css_part + body_part
    import streamlit.components.v1 as components
    components.html(modal_html, height=0)

    # 모달을 여는 자바스크립트 함수를 페이지에 등록
    if "modal_open_functions" not in st.session_state:
        st.session_state["modal_open_functions"] = []
    st.session_state["modal_open_functions"].append(
        f"document.getElementById('{source_id}').classList.add('show');"
    )