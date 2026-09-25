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
from ui.pages._passage_commentary_tab import render_passage_commentary_tab
from ui.pages.sermon_draft import render_sermon_draft_page
from core.generation import SERMON_FORMATS


def render_sermon_workspace_page() -> None:
    """[NAE Phase 1 화면 통합] "설교 연구"(허브)와 "설교문 작성"을 하나의
    사이드바 진입점으로 묶는다. st.tabs는 코드에서 활성 탭을 바꿀 수
    없어(Streamlit 제약) "이어가기" 버튼 클릭 시 자동 전환이 안 되므로,
    이미 이 코드베이스의 nav_page와 동일한 "session_state 키 + st.radio"
    패턴으로 전환한다(ui/app.py의 nav_page 방식 재사용).
    NAE_PASTOR_FEATURE_REALIGNMENT_REPORT_001.md §4.2 화면2 제안."""
    if "sermon_workspace_view" not in st.session_state:
        st.session_state["sermon_workspace_view"] = "연구"

    view = st.radio(
        "설교 준비 단계",
        ["연구", "작성"],
        key="sermon_workspace_view",
        horizontal=True,
        label_visibility="collapsed",
    )
    if view == "연구":
        render_sermon_research_hub_page()
    else:
        render_sermon_draft_page()


def render_sermon_research_hub_page() -> None:
    """Render the Sermon Research Hub page."""
    _init_state()
    _absorb_selection()

    page = BasePage(title="설교 연구", icon="")
    page.render_header()

    # [ADR-031] "본문 해설" 탭 추가 — 성경뷰어로 지정한 본문에 대해 내서재
    # 근거 해설(각주 포함)을 생성한다. 기존 허브(담긴 자료 없으면 조기
    # 종료)는 "설교 연구" 탭 안으로 그대로 옮긴다.
    tab_hub, tab_passage = st.tabs(["설교 연구", "본문 해설"])
    with tab_hub:
        _render_hub_tab()
    with tab_passage:
        render_passage_commentary_tab()

    page.render_footer()


def _render_hub_tab() -> None:
    state = st.session_state["sermon_research_state"]

    # [ADR-035 §3.1 항목2] 옵트인 자동 수집 토글 — 기본 꺼짐. 켠 사용자는
    # "연구/채팅" 화면에서 검색을 실행할 때마다 상위 결과가 수동 클릭
    # 없이 이 허브에 자동 반영된다(ui/pages/research.py::
    # _maybe_auto_collect_for_sermon_research). 기존 수동 "설교 연구에
    # 추가" 버튼은 계속 동작한다.
    st.toggle(
        "검색할 때 상위 결과 자동 반영",
        key="sermon_research_auto_collect",
        help="켜면 \"연구/채팅\" 화면에서 검색을 실행할 때마다 상위 결과가 "
        "자동으로 여기에 담깁니다. 기본은 꺼짐 — 꺼두면 지금처럼 카드의 "
        "\"설교 연구에 추가\" 버튼으로만 담깁니다.",
    )

    if not state["materials"]:
        st.info(
            "아직 담긴 자료가 없습니다. \"검색·연구\" 화면에서 결과 카드의 "
            "\"설교 연구에 추가\"를 눌러 자료를 모아보세요."
        )
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


def _go_to_sermon_draft() -> None:
    state = st.session_state.get("sermon_research_state")
    if state and state["materials"]:
        _seed_sermon_draft_state(state)
    # [NAE Phase 1 화면 통합] 이전에는 nav_page를 바꿔 별도 최상위
    # 화면("설교문 작성")으로 전환했으나, 두 화면이 render_sermon_workspace_page
    # 아래 탭으로 통합되어 같은 페이지 내부 뷰 전환으로 대체됨.
    st.session_state["sermon_workspace_view"] = "작성"


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
