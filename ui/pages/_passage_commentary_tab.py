"""ui/pages/_passage_commentary_tab.py — "연구하기 > 본문 해설" 탭 (ADR-031).

성경뷰어에서 본문을 고르면, 그 본문과 정합하는 내서재 주석 자료를 근거로
한국어 해설을 생성하고 각주(①②③ + 서지 목록 + 원문 보기)를 붙여 보여준다.
내서재에 관련 자료가 없으면 안내만 표시하고 생성하지 않는다.

오케스트레이션 세부는 `core/passage_commentary.py` 참고 — 이 모듈은 Streamlit
세션·위젯·스트리밍 렌더만 담당한다. 상세 패널 2단 레이아웃은
`ui/pages/chat.py::_render_chat_page_with_detail` 패턴을 따른다.
"""

from __future__ import annotations

import logging

import streamlit as st

from core.bible_text import load_bible_text
from core.config import DEFAULT_REGISTRY_PATH
from core.document_detail import get_document_detail
from core.generation import GenerationService
from core.identity_registry import load_identity_registry
from core.passage_commentary import (
    FootnoteEntry,
    circled_marker,
    make_response_package,
    reference_label,
    render_answer_with_badges,
    retrieve_passage_commentary,
)
from ui.components.detail_panel import render_detail_panel
from ui.components.passage_viewer import render_passage_viewer
from ui.pages.chat import _settings_overrides
from ui.state.query_processor import get_shared_query_processor

logger = logging.getLogger(__name__)

_RESULT_KEY = "sr_passage_result"
_DETAIL_KEY = "sr_passage_detail_selection"
_AUTORUN_KEY = "sr_passage_autorun"


def render_passage_commentary_tab() -> None:
    bible = load_bible_text()
    detail_selection = st.session_state.get(_DETAIL_KEY)

    if detail_selection:
        col_main, col_detail = st.columns([2, 1])
    else:
        col_main, col_detail = st.container(), None

    with col_main:
        _render_main(bible)

    if detail_selection and col_detail is not None:
        with col_detail:
            _render_detail_panel(detail_selection)


# ── 왼쪽: 뷰어 + 해설 ────────────────────────────────────
def _render_main(bible) -> None:
    st.markdown("### 성경뷰어")
    ref = render_passage_viewer(bible, key_prefix="sr_passage")
    if ref is None:
        st.session_state.pop(_RESULT_KEY, None)
        return

    ref_key = [ref.book_id, ref.chapter, ref.verse_start, ref.verse_end]
    label = reference_label(ref)

    ctrl_left, ctrl_right = st.columns([2, 3])
    with ctrl_left:
        go = st.button(f"«{label}» 해설 보기", type="primary", key="sr_passage_go")
    with ctrl_right:
        autorun = st.checkbox(
            "본문을 바꾸면 자동으로 해설", value=True, key=_AUTORUN_KEY
        )

    # 탭은 마운트만으로도 렌더된다(Streamlit st.tabs). 그래서 autorun 은
    # "사용자가 뷰어를 실제로 조작했을 때"만 발동한다 — 첫 진입 시점의
    # 기본 본문(예: 첫 책 1:1)만으로는 검색/생성을 시작하지 않는다.
    first_ref = st.session_state.setdefault("sr_passage_initial_ref", ref_key)
    user_engaged = ref_key != first_ref
    cached = st.session_state.get(_RESULT_KEY)
    has_cached = bool(cached) and cached.get("ref_key") == ref_key
    changed = not cached or cached.get("ref_key") != ref_key

    if go or (autorun and changed and (user_engaged or bool(cached))):
        result = _run(ref, ref_key, label)
        st.session_state[_RESULT_KEY] = result
        _render_result(result)
    elif has_cached:
        _render_result(cached)
    else:
        st.caption("본문을 고르면(또는 «해설 보기» 를 누르면) 내서재 자료로 해설을 만듭니다.")


def _run(ref, ref_key, label) -> dict:
    """검색 → 정합 필터 → (자료 있으면) 스트리밍 생성. 결과 dict 를 세션에 저장 가능한
    형태로 돌려준다."""
    processor = get_shared_query_processor()
    outcome = retrieve_passage_commentary(ref, processor)

    if outcome.status == "retrieval_failed":
        return {"ref_key": ref_key, "label": label, "status": "gen_failed",
                "error": outcome.error, "answer_badged": "", "footnotes": []}
    if outcome.status == "no_material":
        return {"ref_key": ref_key, "label": label, "status": "no_material",
                "answer_badged": "", "footnotes": []}

    pkg, _citations, footnotes = make_response_package(outcome, ref, registry=_load_registry())
    generator = _get_generator()

    placeholder = st.empty()
    parts: list[str] = []
    gen_error = None
    try:
        # 사이드바 "답변 생성 모델"/"답변 창의성" 설정을 채팅 화면과 동일하게 반영한다.
        stream = generator.generate_stream(pkg, **_settings_overrides())
        for piece in stream:
            parts.append(piece)
            placeholder.markdown("".join(parts))
        result = stream.to_result() if hasattr(stream, "to_result") else None
        answer = (getattr(result, "answer", "") if result else "") or "".join(parts)
        gen_error = getattr(result, "error", None) if result else None
    except Exception as e:  # noqa: BLE001 — 생성 실패가 탭을 죽이지 않게
        logger.warning("[passage_commentary_tab] 생성 실패: %s", e)
        placeholder.empty()
        return {"ref_key": ref_key, "label": label, "status": "gen_failed",
                "error": str(e), "answer_badged": "", "footnotes": footnotes}

    placeholder.empty()
    if gen_error:
        return {"ref_key": ref_key, "label": label, "status": "gen_failed",
                "error": gen_error, "answer_badged": "", "footnotes": footnotes}
    return {
        "ref_key": ref_key,
        "label": label,
        "status": "ok",
        "answer_badged": render_answer_with_badges(answer, len(footnotes)),
        "footnotes": footnotes,
    }


def _render_result(result: dict) -> None:
    label = result["label"]
    status = result["status"]

    if status == "no_material":
        st.info(
            f"내서재에 «{label}» 본문과 직접 관련된 주석 자료가 없습니다. "
            "«자료 등록» 에서 이 본문을 다루는 주석서를 추가하면 해설을 만들 수 있습니다."
        )
        return
    if status == "gen_failed":
        msg = "해설 생성 중 문제가 발생했습니다. 잠시 후 다시 시도해주세요."
        if result.get("error"):
            msg += f"\n\n({result['error']})"
        st.warning(msg)
        return

    st.markdown(f"#### «{label}» 본문 이해 도움")
    st.markdown(result["answer_badged"] or "_생성된 해설이 없습니다._")

    footnotes = result.get("footnotes") or []
    if footnotes:
        st.markdown("---")
        st.markdown("**참고 자료 (내서재)**")
        for fn in footnotes:
            _render_footnote(fn)


def _render_footnote(fn: FootnoteEntry) -> None:
    marker = circled_marker(fn.marker)
    text_col, btn_col = st.columns([9, 2])
    with text_col:
        st.markdown(f"{marker} {fn.formatted()}")
        if fn.excerpt:
            st.caption(f"{fn.excerpt}…")
    with btn_col:
        if fn.document_id and fn.source_file:
            key = f"sr_pf_view_{fn.marker}_{abs(hash(fn.document_id)) & 0xFFFFFF:x}"
            if st.button("원문 보기", key=key, use_container_width=True):
                st.session_state[_DETAIL_KEY] = {
                    "source_file": fn.source_file,
                    "document_id": fn.document_id,
                    "query_terms": [],
                }
                st.rerun()


# ── 오른쪽: 문서 상세 패널 ───────────────────────────────
def _render_detail_panel(detail_selection: dict) -> None:
    if st.button("닫기", key="sr_passage_detail_close", type="primary"):
        st.session_state[_DETAIL_KEY] = None
        st.rerun()

    st.divider()
    query_terms = detail_selection.get("query_terms", [])
    detail = get_document_detail(
        source_file=detail_selection["source_file"],
        document_id=detail_selection["document_id"],
        query_terms=query_terms,
    )
    render_detail_panel(detail, query_terms)


def _get_generator() -> GenerationService:
    if "sr_passage_generation_service" not in st.session_state:
        st.session_state["sr_passage_generation_service"] = GenerationService()
    return st.session_state["sr_passage_generation_service"]


def _load_registry() -> dict | None:
    """각주 서지(저자·제목·자료유형·연도)를 실제 레코드에서 채우기 위한
    identity registry. 실패해도 각주는 후보 메타데이터로 폴백하므로 None 허용."""
    try:
        return load_identity_registry(DEFAULT_REGISTRY_PATH)
    except Exception as e:  # noqa: BLE001
        logger.warning("[passage_commentary_tab] registry 로드 실패 (각주는 폴백): %s", e)
        return None
