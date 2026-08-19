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
from core.config import DEFAULT_RAW_DIR, DEFAULT_REGISTRY_PATH, SUPPORTED_EXTENSIONS
from core.extractors import extract_text_from_file
from core.identity_registry import find_by_source_file, load_identity_registry
from core.multi_doc_splitter import (
    split_sermon_collection, manual_split, guess_new_sermon_metadata,
    save_sermon_record, infer_collection_year, fill_missing_dates, SermonRecord,
)


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
    _render_save_as_document(records)
    _render_manual_split(records)

    page.render_footer()


def _list_candidate_files() -> list[str]:
    """RAW 폴더에서 설교 모음 후보 파일만 나열한다.

    [2026-07-24, 사용자 요청] "설교문으로 특정되지 않은 것은 리스트
    하지 마라" — identity_registry에 doc_type이 이미 "주석"/"사전"/
    "논문"/"조직신학"/"기타"로 명시적으로 분류된 파일(설교가 아님이
    확정된 것)은 제외한다. 아직 처리 전이라 registry에 없거나
    doc_type이 비어있는 파일은 아직 "설교가 아니다"라고 확정된 게
    아니므로 포함한다(과잉 제외 방지)."""
    raw_dir = Path(DEFAULT_RAW_DIR)
    if not raw_dir.exists():
        return []
    candidates = sorted(
        f.name for f in raw_dir.rglob("*")
        if f.is_file() and not f.name.startswith(".") and f.suffix.lower() in SUPPORTED_EXTENSIONS
    )

    registry_path = Path(DEFAULT_REGISTRY_PATH)
    if not registry_path.exists():
        return candidates
    registry = load_identity_registry(str(registry_path))

    def _is_confirmed_non_sermon(filename: str) -> bool:
        record = find_by_source_file(registry, filename)
        if record is None:
            return False
        doc_type = record.get("doc_type")
        return bool(doc_type) and doc_type != "설교"

    return [f for f in candidates if not _is_confirmed_non_sermon(f)]


def _render_file_selector() -> None:
    files = _list_candidate_files()
    if not files:
        st.warning("보관함에 파일이 없습니다.")
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
        # [2026-07-24, 사용자 요청] "설교뭉치 파일이 설교별로 리스트
        # 되면 개별 설교로 저장하라 — 나중에 제목/날짜/성구별 통계를
        # 낼 것" — 자동 분리된 설교는 여기서 바로 개별 문서로 저장한다.
        # 날짜를 못 찾은 건 저장에서 통째로 빠지지 않도록, 연도를
        # 추정해 "{연도}-12-31" 더미 날짜를 채운 뒤 저장한다(실제 날짜
        # 아님을 12/31로 구분). 제목/성구까지 없는 건 여전히 저장 보류.
        dummy_dates_filled = 0
        if records:
            year = infer_collection_year(records, selected)
            if year is not None:
                dummy_dates_filled = fill_missing_dates(records, year)
            st.session_state["sermon_review_save_summary"] = (
                *_auto_save_records(records), dummy_dates_filled,
            )
        st.rerun()

    source = st.session_state.get("sermon_review_source")
    if source:
        st.caption(f"현재 불러온 파일: {source}")

    summary = st.session_state.get("sermon_review_save_summary")
    if summary:
        saved, already, incomplete, dummy_dates = summary
        st.info(
            f"개별 문서 자동 저장: {saved}건 저장됨"
            + (f" (이 중 {dummy_dates}건은 날짜를 못 찾아 연말 더미 날짜로 채움)" if dummy_dates else "")
            + (f", {already}건 이미 저장돼 있음" if already else "")
            + (f", {incomplete}건은 제목/성구 누락으로 보류(아래에서 채운 뒤 개별 저장하세요)" if incomplete else "")
        )


def _auto_save_records(records: list[SermonRecord]) -> tuple[int, int, int]:
    """자동 분리된 설교들을 개별 문서로 일괄 저장한다.
    Returns: (신규 저장, 이미 존재해서 건너뜀, 필수 항목 누락으로 보류)"""
    saved = already_exists = incomplete = 0
    for record in records:
        try:
            save_sermon_record(record, DEFAULT_RAW_DIR)
            saved += 1
        except FileExistsError:
            already_exists += 1
        except ValueError:
            incomplete += 1
    return saved, already_exists, incomplete


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


def _render_save_as_document(records: list[SermonRecord]) -> None:
    """[2026-07-24, 사용자 요청] 리뷰 중인 설교 1건을 개별 문서로 저장
    — data/RAW/설교_분리/ 밑에 .md 파일로 써서, 기존 처리 파이프라인
    (Processing 페이지)이 다른 RAW 파일과 동일하게 인식하게 한다.
    새 인제스트 경로를 만들지 않고 기존 흐름을 재사용하는 설계.

    제목/날짜/성구 셋 다 있어야 저장 가능 — core.multi_doc_splitter.
    save_sermon_record()가 강제하며, 여기서는 버튼 비활성화로 먼저
    막는다(방어적 이중 검증, manual_split과 동일한 패턴)."""
    index = st.session_state.get("sermon_review_index", 0)
    record = records[index]

    missing = [
        label for label, value in (("제목", record.title), ("날짜", record.date), ("성구", record.scripture))
        if not (value or "").strip()
    ]

    st.divider()
    if missing:
        st.caption(f"⚠️ 개별 문서로 저장하려면 {', '.join(missing)}이(가) 필요합니다 — 위 수동 분할에서 채워주세요.")
        return

    if st.button("💾 이 설교를 개별 문서로 저장", key=f"sermon_save_{index}"):
        try:
            path = save_sermon_record(record, DEFAULT_RAW_DIR)
        except FileExistsError as e:
            st.error(f"[저장 실패] {e}")
            return
        except ValueError as e:
            st.error(f"[저장 실패] {e}")
            return
        st.success(f"저장 완료: {Path(path).name} — Dashboard의 \"🆕 미처리\" 카드에서 처리하러 갈 수 있습니다.")


def _render_manual_split(records: list[SermonRecord]) -> None:
    """자동 분리("제목:" 앵커)가 놓쳐서 한 조각 안에 실제로는 설교
    2개가 남아있는 경우, 사용자가 본문을 훑어보고 지정한 줄부터를
    새 설교로 떼어낸다(core.multi_doc_splitter.manual_split()).
    떼어낸 뒤에는 목록에 새 항목으로 추가되고, 리스트/네비게이션은
    다음 rerun에서 그대로 반영된다.

    [2026-07-24, 사용자 요청] 슬라이더로 시행착오하며 자르는 방식이
    느려서, 줄 번호를 붙인 본문을 보여주고 정확한 줄 번호를 직접
    입력하게 바꿨다. 또한 잘린 지점 첫머리에서 제목/날짜/성구를
    자동으로 읽어와(guess_new_sermon_metadata) 입력칸에 미리 채우고,
    못 찾은 항목만 사용자가 채우면 된다."""
    index = st.session_state.get("sermon_review_index", 0)
    record = records[index]
    lines = record.body.split("\n")

    if len(lines) < 2:
        return  # 본문이 한 줄뿐이면 나눌 대상이 없음

    with st.expander("🔀 이 안에 설교가 2개 이상 섞여 있나요? 수동으로 분할"):
        st.caption("아래에서 새 설교가 시작되는 줄 번호를 확인하세요.")
        st.code("\n".join(f"{i + 1:>4} | {line}" for i, line in enumerate(lines)), line_numbers=False, height=300)

        # [버그 수정 2026-07-24] 위 목록의 줄 번호는 1-based(1번째 줄=
        # lines[0])인데, manual_split()의 cut_line은 0-based 분할
        # 인덱스(lines[cut_line:]이 새 설교)라 그대로 넘기면 실제로는
        # 지정한 줄보다 한 줄 뒤부터 잘렸다(사용자 보고로 확인). 화면에
        # 보이는 값은 1-based로 받고, 내부에서만 0-based로 변환한다.
        display_line = st.number_input(
            "몇 번째 줄부터 새 설교로 분리할까요?",
            min_value=2, max_value=len(lines), value=min(len(lines) // 2 + 1, len(lines)), step=1,
            key=f"sermon_split_cut_{index}",
            help="이 줄(포함)부터 끝까지가 새 설교로 떨어져 나갑니다. 위 목록의 줄 번호를 그대로 입력하세요.",
        )
        cut_line = int(display_line) - 1  # 0-based 분할 인덱스로 변환

        guessed_title, guessed_date, guessed_scripture = guess_new_sermon_metadata(lines, cut_line)
        if not any((guessed_title, guessed_date, guessed_scripture)):
            st.caption("⚠️ 잘린 지점에서 제목/날짜/성구를 자동으로 찾지 못했습니다 — 직접 입력하세요.")
        else:
            st.caption("✅ 잘린 지점에서 자동으로 읽어온 값입니다 — 필요하면 수정하세요.")

        # [2026-07-24, 사용자 요청] 제목/날짜/성구 셋 다 필수 — 자동
        # 분리와 달리 수동 보정이라 "모르면 비워둔다"를 허용하지 않는다.
        # core.multi_doc_splitter.manual_split()도 동일하게 강제하므로
        # (방어적 이중 검증), 여기서 비활성화하는 건 UX용 — 우회해서
        # 호출해도 함수 자체가 막는다.
        # 위젯 key에 cut_line을 포함해, 자를 지점이 바뀌면 자동으로
        # 새로 읽어온 값으로 갱신되게 한다(이전 입력이 다른 지점의
        # 값으로 남아 있으면 오히려 혼동을 준다).
        new_title = st.text_input(
            "새로 분리될 설교의 제목(필수)", value=guessed_title or "",
            key=f"sermon_split_title_{index}_{cut_line}",
        )
        col_date, col_scripture = st.columns(2)
        with col_date:
            new_date = st.text_input(
                "날짜(필수, YYYY-MM-DD)", value=guessed_date or "",
                key=f"sermon_split_date_{index}_{cut_line}",
            )
        with col_scripture:
            new_scripture = st.text_input(
                "성구(필수)", value=guessed_scripture or "",
                key=f"sermon_split_scripture_{index}_{cut_line}",
            )

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
