"""내서재 공개 자료 (NAE Public Theology, Beta) — shared render component.

Module gating per ADR-024 §F/§A: `modules.nae_pd.enabled` is the *only*
switch — no second flag. §B/§E: NAE results are never merged into a host
page's primary answer/ranking; this component always renders as its own
self-contained section (own query box, own button, own results) so a host
page can drop it in without touching its existing generation flow.

Originally implemented in `ui/pages/research.py` (ADR-024 §E's designated
integration point); extracted here so `ui/pages/chat.py` (F6,
`docs/NAE_F4_F5_F6_PREPARATION_DESIGN_v1.md`) can reuse the identical
behavior instead of forking a second copy that could drift.

`key_prefix` namespaces Streamlit widget/session_state keys per host page
(e.g. "chat", "research") so the two call sites don't collide if Streamlit
ever keeps both pages' session_state alive at once.
"""
from __future__ import annotations

import re
from typing import Any

import streamlit as st

from NAE.citation_disclosure import get_disclosure


def render_nae_public_section(key_prefix: str) -> None:
    """내서재 공개 자료 검색 섹션 — module gating 준수 (§F).

    nae_pd가 disabled면 아무것도 렌더링하지 않는다. enabled일 때만
    "내서재 공개 자료 (Beta)" 섹션을 표시하고, 호출자의 기존 결과와
    별도 영역으로 보여준다(§B 병합 금지) — 답변 생성이나 인용 목록에
    섞여 들어가지 않는다.
    """
    from core import module_registry

    if not module_registry.is_enabled("nae_pd"):
        return  # §F: disabled면 렌더링하지 않음

    st.divider()
    st.markdown(
        '<h3><span class="material-symbols-outlined" style="font-size:22px; vertical-align:-4px;">menu_book</span> 내서재 공개 자료 (Beta)</h3>',
        unsafe_allow_html=True,
    )
    st.caption("공개 신학 자료 — 별도 검색, 위 답변/인용과 합쳐지지 않습니다")

    query_key = f"{key_prefix}_nae_research_query"
    results_key = f"{key_prefix}_nae_research_results"
    status_key = f"{key_prefix}_nae_search_status"

    nae_query = st.text_input(
        "공개 자료 검색어",
        placeholder="공개 신학 자료에서 검색할 질문을 입력하세요...",
        key=query_key,
    )

    if not nae_query:
        st.info("검색어를 입력하고 '검색'을 클릭하세요.")
        return

    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("검색", type="primary", icon=":material/search:", use_container_width=True, key=f"{key_prefix}_nae_search_btn"):
            nae_results = _execute_nae_retrieval(nae_query)
            st.session_state[results_key] = nae_results
            st.session_state[status_key] = (
                f"결과 {len(nae_results)}건" if nae_results else "결과 없음"
            )

    nae_results = st.session_state.get(results_key)
    nae_status = st.session_state.get(status_key, "")

    if not nae_results and not nae_status:
        return

    if nae_status:
        st.caption(nae_status)

    if not nae_results:
        st.info("공개 자료에서 일치하는 결과가 없습니다.")
        return

    for i, item in enumerate(nae_results, 1):
        if isinstance(item, dict):
            _render_nae_paragraph_card(i, item)
        else:
            _render_nae_legacy_card(i, item)


def _render_nae_paragraph_card(i: int, hit: dict) -> None:
    """옵션 A — 완성 문단 형태 근거 카드 (PM 정렬 감사 선결 #4)."""
    bib = hit.get("bibliography") or {}
    score = hit.get("retrieval_score", 0) or 0
    paragraph = (hit.get("evidence_paragraph") or "").strip()
    anchor = (hit.get("anchor_sentence") or "").strip()
    work = bib.get("work") or "Unknown Work"
    author = bib.get("author") or "Unknown"
    ps, pe = bib.get("page_start"), bib.get("page_end")
    page_str = f"p.{ps}–{pe}" if ps and pe and ps != pe else (f"p.{ps}" if ps else "")
    para_idx = bib.get("paragraph_index")

    with st.container():
        st.markdown(f"**{i}. {work}**")
        bib_line = " · ".join(
            x for x in [author, page_str, (f"§{para_idx}" if para_idx is not None else "")] if x
        )
        st.caption(f"Score: {score:.4f} | {bib_line}")

        authority_class = hit.get("authority_class")
        if authority_class:
            st.caption(f"자료 등급: {authority_class}")

        disclosure = get_disclosure(authority_class)
        if disclosure:
            st.warning(disclosure)  # ADR-030 Amendment A §6 — F6 UI 필수 노출

        if not hit.get("paragraph_resolved", True):
            st.caption("⚠ 원문 문단 복원 실패 — 문장 근거만 표시합니다.")

        st.markdown(paragraph if paragraph else "_(근거 본문 없음)_")

        if anchor and anchor in paragraph:
            st.info(f"이 문단에서 질의와 일치한 문장: {anchor}")

        if re.search(r"[぀-ヿ一-鿿]", paragraph):
            st.caption("⚠ 원문에 비-라틴 문자(OCR/모델 노이즈 가능)가 포함되어 있습니다.")

        claim = hit.get("claim")
        if claim:
            with st.expander("AI 요지 요약 (원문 아님)"):
                st.caption("AI가 생성한 한국어 요약입니다. 근거는 위 원문 문단입니다.")
                st.write(claim)

        if hit.get("tsu_id"):
            st.caption(f"출처 ID: {hit['tsu_id']}")


def _render_nae_legacy_card(i: int, citation: Any) -> None:
    """NAE_PARAGRAPH_EVIDENCE=0 또는 폴백 — 종전 Citation 객체 카드."""
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
        from NAE.retrieval_adapter import (
            bridge_query,
            bridge_query_paragraphs,
            NaePdModuleDisabledError,
        )
        from NAE.answer_context import paragraph_evidence_enabled

        if paragraph_evidence_enabled():
            return bridge_query_paragraphs(query, top_k=10, limit_check=True) or []
        return bridge_query(query, top_k=10, limit_check=True) or []

    except NaePdModuleDisabledError:
        st.error("공개 자료 모듈이 비활성화되었습니다. config.yaml에서 nae_pd.enabled: true로 설정하세요.")
        return []

    except Exception:  # noqa: BLE001 — §G fail-closed
        st.warning("공개 자료 검색 중 오류가 발생했습니다. (fail-closed: 빈 결과)")
        return []
