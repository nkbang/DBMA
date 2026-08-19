"""DBMA — 설교 연구 허브 (UX-007 §7).

검색·연구에서 고른 자료가 끊기지 않고 설교 준비로 이어지는 staging
공간. 이번 이터레이션은 스펙이 명시한 "수동 입력 UI까지"만 구현한다
— Research→Sermon Draft 어댑터(자동 전달)는 별도 이터레이션.

상태 설계 근거: docs/DBMA-UX-007-SessionState-Design.md §2 (Tier B).
- sermon_research_selection: 검색·연구 화면이 채우는 전환 버퍼(list)
- sermon_research_state: 이 화면이 관리하는 작업 상태(materials/notes/
  outline_draft) — 브라우저 세션 한정, Core/retrieval 무변경
"""

import streamlit as st

from ui.pages._base import BasePage


def render_sermon_research_hub_page() -> None:
    """Render the Sermon Research Hub page."""
    _init_state()
    _absorb_selection()

    page = BasePage(title="설교 연구", icon="")
    page.render_header()

    state = st.session_state["sermon_research_state"]

    if not state["materials"]:
        st.info(
            "아직 담긴 자료가 없습니다. \"검색·연구\" 화면에서 결과 카드의 "
            "\"설교 연구에 추가\"를 눌러 자료를 모아보세요."
        )
        page.render_footer()
        return

    col_left, col_right = st.columns(2)
    with col_left:
        st.markdown("### 선택한 자료")
        _render_materials(state)
    with col_right:
        st.markdown("### 개요 초안")
        _render_outline(state)

    st.divider()
    st.caption(
        "이번 단계에서는 자료·메모·개요가 설교 준비 화면으로 자동 "
        "전달되지 않습니다 — \"이어가기\"는 화면 전환만 하며, 내용은 "
        "직접 옮겨 적어야 합니다(자동 전달은 다음 이터레이션에서 추가)."
    )
    st.button(
        "설교 작성으로 이어가기",
        type="primary",
        on_click=_go_to_sermon_draft,
    )

    page.render_footer()


def _go_to_sermon_draft() -> None:
    st.session_state["nav_page"] = "설교문 작성"


def _init_state() -> None:
    if "sermon_research_state" not in st.session_state:
        st.session_state["sermon_research_state"] = {
            "status": "collecting",
            "materials": [],
            "notes": {},
            "outline_draft": [],
        }


def _absorb_selection() -> None:
    """sermon_research_selection(전환 버퍼)에 새로 쌓인 항목만 흡수한다.
    tsu_id 기준으로 중복 제거 — 버퍼는 흡수 후 비운다(누적 append 버퍼이므로
    research_detail_selection처럼 단일 값이 아니라 리스트를 통째로 소비)."""
    pending = st.session_state.get("sermon_research_selection", [])
    if not pending:
        return

    state = st.session_state["sermon_research_state"]
    existing_ids = {m.get("tsu_id") for m in state["materials"]}
    for item in pending:
        tsu_id = item.get("tsu_id")
        if tsu_id and tsu_id not in existing_ids:
            state["materials"].append(item)
            existing_ids.add(tsu_id)

    st.session_state["sermon_research_selection"] = []


def _render_materials(state: dict) -> None:
    for i, material in enumerate(state["materials"]):
        tsu_id = material.get("tsu_id", f"_idx{i}")
        with st.container(border=True):
            st.markdown(f"**{material.get('source_label') or '출처 미상'}**")
            excerpt = material.get("excerpt", "")
            if excerpt:
                st.caption(excerpt)

            note_value = state["notes"].get(tsu_id, "")
            new_note = st.text_area(
                "메모",
                value=note_value,
                key=f"sermon_note_{tsu_id}",
                label_visibility="collapsed",
                placeholder="메모를 남겨보세요",
            )
            state["notes"][tsu_id] = new_note

            if st.button("제거", key=f"sermon_remove_{tsu_id}"):
                state["materials"].pop(i)
                state["notes"].pop(tsu_id, None)
                st.rerun()


def _render_outline(state: dict) -> None:
    outline_text = "\n".join(state["outline_draft"])
    new_text = st.text_area(
        "개요 (한 줄에 한 단계)",
        value=outline_text,
        height=200,
        key="sermon_outline_draft_input",
        placeholder="예:\n1. 본문 소개\n2. 핵심 주제\n3. 적용",
    )
    state["outline_draft"] = [line for line in new_text.splitlines() if line.strip()]
