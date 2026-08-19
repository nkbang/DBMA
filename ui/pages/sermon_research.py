"""DBMA — 설교 연구 허브 (UX-007 §7).

검색·연구에서 고른 자료가 끊기지 않고 설교 준비로 이어지는 staging
공간. §7 어댑터(materials/notes/outline_draft를 sermon_draft_state
초기값으로 프리필)까지 포함 — candidates/outline은 채우지 않고 정상
검색 경로를 그대로 타게 둔다(design doc §4 표 결정).

상태 설계 근거: docs/DBMA-UX-007-SessionState-Design.md §2/§4.
- sermon_research_selection: 검색·연구 화면이 채우는 전환 버퍼(list)
- sermon_research_state: 이 화면이 관리하는 작업 상태(materials/notes/
  outline_draft) — 브라우저 세션 한정, Core/retrieval 무변경
"""

import streamlit as st

from ui.pages._base import BasePage
from core.generation import SERMON_FORMATS


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
        "\"이어가기\"를 누르면 선택한 자료·메모·개요가 설교 준비 화면의 "
        "\"본문과 주제\" 입력란에 초안으로 채워집니다 — 검색 후보와 "
        "생성된 개요까지 자동으로 이어지지는 않으니(설교 준비는 그 "
        "시점에 정상적으로 다시 검색합니다), 채워진 내용은 자유롭게 "
        "고쳐서 쓰면 됩니다."
    )
    st.button(
        "설교 작성으로 이어가기",
        type="primary",
        on_click=_go_to_sermon_draft,
    )

    page.render_footer()


def _go_to_sermon_draft() -> None:
    state = st.session_state.get("sermon_research_state")
    if state and state["materials"]:
        _seed_sermon_draft_state(state)
    st.session_state["nav_page"] = "설교문 작성"


def _seed_sermon_draft_state(state: dict) -> None:
    """§7 어댑터 (design doc §4 표). 이미 진행 중인 초안(개요 생성 이후
    단계, 또는 사용자가 직접 입력해둔 본문/주제)이 있으면 덮어쓰지
    않는다 — "이어가기"는 새로 시작하는 세션을 위한 프리필이지, 진행
    중인 작업을 대체하는 기능이 아니다."""
    existing = st.session_state.get("sermon_draft_state")
    if existing and existing.get("status") != "input":
        return
    if existing and existing.get("scripture_and_theme", "").strip():
        return

    seed = _build_sermon_draft_seed(state)
    st.session_state["sermon_draft_state"] = {
        "status": "input",
        "scripture_and_theme": seed["scripture_and_theme"],
        "style_files": seed["style_files"],
        "sermon_format": SERMON_FORMATS[0],
        "outline": None,
        "candidates": [],
        "expanded": {},
    }
    # sermon_draft.py의 text_area는 value=와 key=를 함께 쓴다 — 위젯이
    # 한 번 렌더된 뒤에는 key로 저장된 session_state 값이 value=보다
    # 우선하므로, state 딕셔너리만 바꾸면 rerun 후에도 빈 채로 남는다
    # (sermon_draft.py:135-142에서 이미 지적된 동일 패턴, 위젯 키에도
    # 같이 써야 한다).
    st.session_state["sermon_input_text"] = seed["scripture_and_theme"]


def _build_sermon_draft_seed(state: dict) -> dict:
    """materials/notes/outline_draft -> sermon_draft_state 초기값.
    candidates/outline은 채우지 않는다 — core/generation.py의
    RankedCandidate 구조와 결합하는 대신, 폼 제출 시 정상적인
    QueryProcessor 재검색 경로를 그대로 타게 둔다(design doc §4)."""
    lines = []
    for material in state["materials"]:
        label = material.get("source_label") or "출처 미상"
        excerpt = material.get("excerpt", "")
        note = state["notes"].get(material.get("tsu_id"), "")
        line = f"- {label}"
        if excerpt:
            line += f": {excerpt}"
        if note:
            line += f" (메모: {note})"
        lines.append(line)

    if state["outline_draft"]:
        lines.append("")
        lines.append("개요 초안:")
        lines.extend(f"  {i + 1}. {step}" for i, step in enumerate(state["outline_draft"]))

    return {
        "scripture_and_theme": "\n".join(lines),
        "style_files": _match_style_files(state),
    }


def _match_style_files(state: dict) -> list[str]:
    """선택한 자료의 source_label이 실제 코퍼스 source_file과 일치하면
    style_files 후보로 채운다 — 매칭 안 되면 빈 리스트(추측 금지).
    Retrieval Engine이 이 세션에서 아직 로드된 적 없으면(비용이 큰
    코퍼스 로드를 이 편의 기능만을 위해 새로 트리거하지 않기 위해)
    매칭을 시도하지 않고 빈 리스트를 반환한다."""
    processor = st.session_state.get("shared_query_processor")
    if processor is None:
        return []

    try:
        available_files = set(processor.engine.list_source_files())
    except Exception:
        return []

    seen: set[str] = set()
    matched: list[str] = []
    for material in state["materials"]:
        label = material.get("source_label")
        if label and label in available_files and label not in seen:
            matched.append(label)
            seen.add(label)
    return matched


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
