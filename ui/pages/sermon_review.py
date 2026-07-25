"""DBMA Design System — Sermon Review Page.

설교 모음 파일(한 파일에 1년치 등 여러 설교가 들어있는 경우) 하나를
core.multi_doc_splitter.split_sermon_collection()으로 분리한 뒤,
날짜(주일)별로 — 같은 날짜에 여러 설교가 있으면 제목별로 — 한 편씩
넘겨보며 검수하는 뷰어.

Scope: 이 페이지는 리뷰(읽기)만 담당한다. 분리된 설교를 실제 TSU/
identity_registry에 개별 문서로 등록하는 단계는 별도 범위(아직 미구현,
2026-07-24 세션에서 명시적으로 범위 밖으로 남김).
"""

from pathlib import Path

import streamlit as st

from ui.pages._base import BasePage
from core.config import DEFAULT_RAW_DIR, SUPPORTED_EXTENSIONS
from core.extractors import extract_text_from_file
from core.multi_doc_splitter import split_sermon_collection, manual_split, SermonRecord


def render_sermon_review_page() -> None:
    """Render the Sermon Review page."""
    page = BasePage(title="설교 리뷰", icon="🗂️")
    page.render_header()

    _render_file_selector()

    records = st.session_state.get("sermon_review_records")
    if records is None:
        page.render_footer()
        return

    if not records:
        st.info("이 파일에서 \"제목:\"으로 시작하는 줄을 찾지 못했습니다 — 여러 설교가 아니라 단일 문서로 보입니다.")
        page.render_footer()
        return

    _render_sermon_navigator(records)
    _render_selected_sermon(records)
    _render_manual_split(records)

    page.render_footer()


def _list_candidate_files() -> list[str]:
    raw_dir = Path(DEFAULT_RAW_DIR)
    if not raw_dir.exists():
        return []
    return sorted(
        f.name for f in raw_dir.rglob("*")
        if f.is_file() and not f.name.startswith(".") and f.suffix.lower() in SUPPORTED_EXTENSIONS
    )


def _render_file_selector() -> None:
    files = _list_candidate_files()
    if not files:
        st.warning("RAW 폴더에 파일이 없습니다.")
        return

    selected = st.selectbox("설교 모음 파일 선택", options=files, key="sermon_review_file")

    if st.button("불러오기 / 분리하기", key="sermon_review_load"):
        path = str(Path(DEFAULT_RAW_DIR) / selected)
        with st.spinner("추출 및 분리 중..."):
            try:
                text = extract_text_from_file(path)["text"]
                records = split_sermon_collection(text)
            except Exception as e:
                st.error(f"[처리 실패] {e}")
                return
        st.session_state["sermon_review_records"] = records
        st.session_state["sermon_review_index"] = 0
        st.session_state["sermon_review_source"] = selected
        st.rerun()

    source = st.session_state.get("sermon_review_source")
    if source:
        st.caption(f"현재 불러온 파일: {source}")


def _sermon_label(record: SermonRecord) -> str:
    date_part = record.date or "날짜 미상"
    return f"{date_part} · {record.title}"


def _render_sermon_navigator(records: list[SermonRecord]) -> None:
    """주일(날짜)별 — 같은 날짜면 제목별로 — 정렬된 목록에서 하나를
    고르거나 이전/다음으로 넘긴다. 날짜 없는 설교는 맨 뒤로 밀려서
    "날짜순" 흐름을 방해하지 않는다."""
    ordered_indices = sorted(
        range(len(records)),
        key=lambda i: (records[i].date is None, records[i].date or "", records[i].title),
    )

    current_index = st.session_state.get("sermon_review_index", 0)
    if current_index not in ordered_indices:
        current_index = ordered_indices[0]

    position = ordered_indices.index(current_index)

    col_prev, col_select, col_next = st.columns([1, 4, 1])
    with col_prev:
        if st.button("◀ 이전", disabled=(position == 0), use_container_width=True):
            st.session_state["sermon_review_index"] = ordered_indices[position - 1]
            st.rerun()
    with col_select:
        labels = [_sermon_label(records[i]) for i in ordered_indices]
        chosen_label = st.selectbox(
            "설교 선택", options=labels, index=position,
            key="sermon_review_select", label_visibility="collapsed",
        )
        chosen_position = labels.index(chosen_label)
        if ordered_indices[chosen_position] != current_index:
            st.session_state["sermon_review_index"] = ordered_indices[chosen_position]
            st.rerun()
    with col_next:
        if st.button("다음 ▶", disabled=(position == len(ordered_indices) - 1), use_container_width=True):
            st.session_state["sermon_review_index"] = ordered_indices[position + 1]
            st.rerun()

    st.caption(f"{position + 1} / {len(ordered_indices)}편")


def _render_selected_sermon(records: list[SermonRecord]) -> None:
    index = st.session_state.get("sermon_review_index", 0)
    record = records[index]

    st.divider()
    st.markdown(f"### {record.title}")
    meta_parts = []
    if record.date:
        meta_parts.append(f"📅 {record.date}")
    else:
        meta_parts.append("📅 날짜 미상")
    if record.scripture:
        meta_parts.append(f"📖 {record.scripture}")
    st.caption(" · ".join(meta_parts))

    st.markdown(record.body if record.body else "_본문 없음_")


def _render_manual_split(records: list[SermonRecord]) -> None:
    """자동 분리("제목:" 앵커)가 놓쳐서 한 조각 안에 실제로는 설교
    2개가 남아있는 경우, 사용자가 본문을 훑어보고 지정한 줄부터를
    새 설교로 떼어낸다(core.multi_doc_splitter.manual_split()).
    떼어낸 뒤에는 목록에 새 항목으로 추가되고, 리스트/네비게이션은
    다음 rerun에서 그대로 반영된다."""
    index = st.session_state.get("sermon_review_index", 0)
    record = records[index]
    lines = record.body.split("\n")

    if len(lines) < 2:
        return  # 본문이 한 줄뿐이면 나눌 대상이 없음

    with st.expander("🔀 이 안에 설교가 2개 이상 섞여 있나요? 수동으로 분할"):
        cut_line = st.slider(
            "몇 번째 줄부터 새 설교로 분리할까요?",
            min_value=1, max_value=len(lines) - 1, value=len(lines) // 2,
            key=f"sermon_split_cut_{index}",
            help="이 줄부터(포함) 끝까지가 새 설교로 떨어져 나갑니다.",
        )

        col_before, col_after = st.columns(2)
        with col_before:
            st.caption("분할 전 마지막 부분(기존 설교)")
            st.text("\n".join(lines[max(0, cut_line - 3):cut_line]))
        with col_after:
            st.caption("분할 후 시작 부분(새 설교)")
            st.text("\n".join(lines[cut_line:cut_line + 3]))

        # [2026-07-24, 사용자 요청] 제목/날짜/성구 셋 다 필수 — 자동
        # 분리와 달리 수동 보정이라 "모르면 비워둔다"를 허용하지 않는다.
        # core.multi_doc_splitter.manual_split()도 동일하게 강제하므로
        # (방어적 이중 검증), 여기서 비활성화하는 건 UX용 — 우회해서
        # 호출해도 함수 자체가 막는다.
        new_title = st.text_input("새로 분리될 설교의 제목(필수)", key=f"sermon_split_title_{index}")
        col_date, col_scripture = st.columns(2)
        with col_date:
            new_date = st.text_input("날짜(필수, YYYY-MM-DD)", key=f"sermon_split_date_{index}")
        with col_scripture:
            new_scripture = st.text_input("성구(필수)", key=f"sermon_split_scripture_{index}")

        missing = [
            label for label, value in (("제목", new_title), ("날짜", new_date), ("성구", new_scripture))
            if not value.strip()
        ]
        if missing:
            st.caption(f"⚠️ 아직 입력 안 됨: {', '.join(missing)} — 전부 입력해야 분할할 수 있습니다.")

        if st.button("✂️ 이 지점에서 분할 실행", disabled=bool(missing), key=f"sermon_split_go_{index}"):
            try:
                first, second = manual_split(
                    record,
                    cut_line=cut_line,
                    new_title=new_title.strip(),
                    new_date=new_date.strip(),
                    new_scripture=new_scripture.strip(),
                )
            except ValueError as e:
                st.error(f"[분할 실패] {e}")
                return
            records[index] = first
            records.insert(index + 1, second)
            st.session_state["sermon_review_records"] = records
            st.session_state["sermon_review_index"] = index
            st.success(f"분할 완료 — \"{second.title}\"이(가) 새 설교로 추가되었습니다.")
            st.rerun()
