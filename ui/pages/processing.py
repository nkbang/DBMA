"""DBMA Design System — Document Processing Page.

Document ingestion and processing workflow interface.
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Any, Dict, List

import streamlit as st
from pathlib import Path

from ui.pages._base import BasePage
from ui.theme.colors import THEME
from ui.components.status import progress_indicator, status_badge
from ui.state.store import StateStore
from core.config import DEFAULT_RAW_DIR, DEFAULT_OUTPUT_DIR
from ui.state.background_builder import get_shared_background_builder
from core.extraction_failures import load_extraction_failures
from core.processing import (
    build_converter,
    build_splitter,
    process_batch,
    get_processed_files,
)
from core.utils import make_safe_stem

logger = logging.getLogger(__name__)

# [SPRINT22-A] Single source of truth for supported intake formats — the
# extractor (core/extractors.py::extract_text_from_file) has always
# supported pdf/txt/md/docx/epub/html/htm/rtf, but this UI independently
# repeated a stale {pdf,txt,md,docx}-only set in three separate literals
# (SPRINT21-G-3-B backlog item), silently hiding epub/html/rtf from users.
# One constant now, referenced everywhere a supported-extension check is
# needed, so the two can't drift apart again.
SUPPORTED_EXTS = {".pdf", ".txt", ".md", ".docx", ".epub", ".html", ".htm", ".rtf"}

# [SPRINT25-B-2] Human-readable labels for the exception classes actually
# reachable in the extraction path (verified in SPRINT25-B-1 Preflight —
# never guessed). An error_type not in this map is shown verbatim, so a new
# exception class surfaces its raw name rather than a wrong label.
_ERROR_TYPE_LABELS = {
    "FileNotFoundError": "파일 없음",
    "ValueError": "형식/추출 오류",
    "PackageNotFoundError": "손상된 DOCX",
    "EpubException": "손상된 EPUB",
}


def _failure_label(failure: dict) -> str:
    """Display label for one failure record. exception-stage failures are
    refined by error_type (SPRINT25-B-1); everything else uses the stage.
    Missing error_type (legacy records) falls back to the generic stage
    label, so nothing regresses."""
    stage_labels = {"extract": "추출 실패", "noise": "정제 후 텍스트 없음", "exception": "예외 발생"}
    if failure.get("stage") == "exception" and failure.get("error_type"):
        et = failure["error_type"]
        return _ERROR_TYPE_LABELS.get(et, et)
    return stage_labels.get(failure.get("stage"), failure.get("stage", "?"))


def render_processing_page() -> None:
    """Render the DBMA Document Processing page."""
    page = BasePage(title="문서 처리", icon="📄")
    page.render_header()

    # ── File Upload (Drag & Drop) ───────────────────────────────
    page.render_section("파일 업로드", icon="📤")
    _render_upload_section()

    # ── Ingestion Form ─────────────────────────────────────────
    page.render_section("문서 처리", icon="📥")
    _render_ingestion_form()

    # ── Processing Queue ───────────────────────────────────────
    page.render_section("처리 대기열", icon="📋")
    _render_processing_queue()

    # ── Processing History ─────────────────────────────────────
    page.render_section("처리 기록", icon="📜")
    _render_processing_history()

    # ── Recent Failures ──────────────────────────────────────────
    page.render_section("최근 실패", icon="⚠️")
    _render_recent_failures()

    page.render_footer()


def _render_upload_section() -> None:
    """[SPRINT22-A] Drag & drop file upload.

    Saves uploaded files directly into DEFAULT_RAW_DIR and stops there —
    it is purely an alternate intake mechanism for RAW. The existing
    processing pipeline (_build_file_list/process_batch/process_one_file)
    picks the saved files up completely unchanged on the next "🚀 문서
    처리 시작" click, exactly as if the user had copied them into RAW
    manually. No core/processing.py changes needed.
    """
    uploaded_files = st.file_uploader(
        "파일을 끌어다 놓거나 선택하세요",
        type=sorted(ext.lstrip(".") for ext in SUPPORTED_EXTS),
        accept_multiple_files=True,
        key="raw_upload_files",
    )

    if not uploaded_files:
        st.caption("지원 형식: PDF, TXT, MD, DOCX, EPUB, HTML, RTF")
        return

    st.caption(f"{len(uploaded_files)}개 파일 선택됨: {', '.join(f.name for f in uploaded_files)}")

    if st.button("📥 RAW 폴더에 저장", key="save_uploads"):
        raw_dir = Path(DEFAULT_RAW_DIR)
        raw_dir.mkdir(parents=True, exist_ok=True)
        saved, skipped = [], []
        for f in uploaded_files:
            # Path(...).name strips any directory components the browser
            # might have supplied — never write outside raw_dir.
            safe_name = Path(f.name).name
            ext = Path(safe_name).suffix.lower()
            if ext not in SUPPORTED_EXTS:
                skipped.append(safe_name)
                continue
            dest = raw_dir / safe_name
            dest.write_bytes(f.getvalue())
            saved.append(safe_name)

        if saved:
            st.success(f"RAW에 저장됨: {', '.join(saved)} — 아래에서 처리를 시작하세요.")
        if skipped:
            st.warning(f"지원하지 않는 형식이라 건너뜀: {', '.join(skipped)}")
        st.rerun()


def _build_file_list(target_dir: str, force_reingest: bool) -> List[Dict[str, Any]]:
    """Build file list from target directory, respecting force_reingest flag."""
    raw_path = Path(target_dir)
    if not raw_path.exists():
        return []

    files = []

    for f in sorted(raw_path.iterdir()):
        if f.suffix.lower() not in SUPPORTED_EXTS:
            continue
        if not f.is_file():
            continue

        name = f.name
        use_ocr = False
        ext = f.suffix.lower().replace(".", "")

        # Check batch_state for already processed files
        output_path = Path(DEFAULT_OUTPUT_DIR)
        state_file = output_path / ".batch_state.json"
        if state_file.exists() and not force_reingest:
            try:
                data = json.loads(state_file.read_text(encoding="utf-8"))
                if name in data.get("processed", []):
                    continue  # Skip already processed files unless force_reingest
            except (json.JSONDecodeError, OSError):
                pass

        files.append({
            "path": str(f),
            "name": name,
            "ext": ext,
            "use_ocr": use_ocr,
        })

    return files


def _filter_selected_files(
    file_list: List[Dict[str, Any]], selected_names: Optional[List[str]]
) -> List[Dict[str, Any]]:
    """[2026-07-21] _build_file_list()가 만든 후보 목록을 사용자가 고른
    파일명(selected_names)으로 좁힌다. selected_names가 None이면(선택
    UI 미표시 — 강제 옵션이 꺼진 일반 처리 경로) 전체 목록을 그대로
    반환해 기존 동작을 바꾸지 않는다. 순서는 항상 file_list 원래 순서를
    따른다(선택 UI에서 고른 순서가 아니라)."""
    if selected_names is None:
        return file_list
    selected_set = set(selected_names)
    return [f for f in file_list if f["name"] in selected_set]


def _render_ingestion_form() -> None:
    """Render the document ingestion form."""
    store = StateStore()

    # Available folders for processing
    _available_dirs: List[str] = []
    _dir_labels: Dict[str, str] = {}
    try:
        _base = Path(DEFAULT_RAW_DIR).parent
        if _base.exists():
            for d in sorted(_base.iterdir()):
                if d.is_dir() and any(f.suffix.lower() in SUPPORTED_EXTS for f in d.iterdir() if f.is_file()):
                    _available_dirs.append(str(d))
                    _dir_labels[str(d)] = f"{d.name} ({len([f for f in d.iterdir() if f.is_file()])} files)"
    except OSError:
        pass

    # Ensure current DEFAULT_RAW_DIR is always available
    if DEFAULT_RAW_DIR not in _available_dirs:
        _available_dirs.insert(0, DEFAULT_RAW_DIR)
        _dir_labels.setdefault(DEFAULT_RAW_DIR, f"기본 RAW 폴더")

    # Helper: open folder in system file browser
    def _open_folder_in_browser(folder_path: str) -> None:
        """Open a folder in the system's native file browser."""
        import platform
        system = platform.system()
        if system == "Darwin":  # macOS
            os.system(f"open '{folder_path}'")
        elif system == "Linux":
            os.system(f"xdg-open '{folder_path}'")
        else:  # Windows
            os.system(f'explorer "{folder_path}"')

    c1, c2, c3 = st.columns([3, 1, 2])
    with c1:
        # Folder selector dropdown
        selected = st.selectbox(
            "처리 대상 폴더",
            options=_available_dirs,
            format_func=lambda x: str(_dir_labels.get(x, "")) if _dir_labels.get(x) else x,
            key="processing_target_selector",
            help="처리할 폴더를 선택하거나 아래에 직접 경로를 입력하세요.",
        )
        # Allow manual override
        manual_dir = st.text_input(
            "또는 직접 경로 입력",
            value=selected if selected != DEFAULT_RAW_DIR else "",
            placeholder=DEFAULT_RAW_DIR,
            key="processing_target_manual",
        )
        target_dir = (manual_dir or "").strip() or selected
        store.set("processing_target", target_dir)

    with c2:
        # "Open Folder" button — opens system file browser at target_dir
        if st.button("📁 폴더 열기", key="open_folder_btn", use_container_width=True):
            _open_folder_in_browser(target_dir)
            st.info(f"'{target_dir}' 폴더를 파일 브라우저에서 열었습니다.")

    with c3:
        # [SPRINT29-B] Labeled "(토큰)" not "(문자)": this value feeds
        # build_splitter() -> SentenceTransformersTokenTextSplitter, which
        # counts tokens, not characters. It also applies only on the
        # fallback path — the primary chunker (optimize_chunks) uses
        # config.yaml chunking.default_size (chars). See help text.
        chunk_size = st.number_input(
            "청크 크기 (토큰, 폴백용)",
            min_value=256,
            max_value=8192,
            value=1000,
            step=256,
            key="chunk_size",
            help="폴백 splitter(토큰 단위)에만 적용됩니다. 정상 처리 시 청킹은 config.yaml의 default_size(문자)를 따릅니다.",
        )
        store.set("chunk_size", chunk_size)

    # Additional options
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        overlap = st.number_input(
            "오버랩 (토큰, 폴백용)",
            min_value=0,
            max_value=500,
            value=200,
            step=50,
            key="chunk_overlap",
            help="폴백 splitter(토큰 단위)에만 적용됩니다.",
        )
    with col2:
        use_ocr = st.checkbox("OCR 사용", value=False, key="use_ocr")
    with col3:
        force_reingest = st.checkbox("강제 재처리", value=False, key="force_reingest",
                                      help="이미 처리된 파일명도 다시 시도합니다. 다만 내용이 기존과 동일하면 여전히 건너뜁니다.")
    with col4:
        store.set("use_ocr", use_ocr)
        store.set("force_reingest", force_reingest)

    # [2026-07-21] force_reingest("강제 재처리")와는 별개 기능 — 파일명
    # 게이트만 우회하는 force_reingest와 달리, 콘텐츠 해시가 동일해도
    # classify_ingest_decision()의 SKIP을 무시하고 실제로 청킹을 다시
    # 실행한다. 청킹 알고리즘 자체를 고친 뒤(예: _merge_sentence_fragments
    # word-safe hard slice 수정) 이미 처리된 문서들을 새 로직으로
    # 재청킹하고 싶을 때 쓴다. 기존 "강제 재처리" 체크박스 의미를 바꾸면
    # tests/test_process_batch_force_reingest.py의 명시적 계약("두 게이트를
    # 혼동하지 말 것")을 깨므로, 반드시 별도 컨트롤로 둔다
    # (tests/test_force_rechunk.py 참고).
    # 엔지니어링 유지보수용 위험 옵션 — 일반 사용자(베타 테스터)에게는 불필요해
    # 숨긴다. NAE_ADMIN_MODE=1일 때만 노출 (ui/app.py의 Monitor 게이트와 동일 패턴).
    if os.environ.get("NAE_ADMIN_MODE") == "1":
        force_rechunk = st.checkbox(
            "⚠️ 전체 재청킹 (내용이 같아도 다시 청킹)", value=False, key="force_rechunk",
            help="청킹 알고리즘이 바뀐 뒤 이미 처리된 문서를 새 로직으로 다시 청킹할 때만 사용하세요. 자동으로 '강제 재처리'도 함께 적용됩니다.",
        )
    else:
        force_rechunk = False
    store.set("force_rechunk", force_rechunk)
    effective_force_reingest = force_reingest or force_rechunk

    # Count pending files
    # [버그 수정 2026-07-21] 이전에는 RAW의 지원 형식 파일 총 개수를 셌다 —
    # 이미 처리 완료된 파일도 포함되어, 대기열이 0개인데 "처리 가능: 64개"로
    # 표시되는 모순이 있었다(사용자 보고). _build_file_list()는 이미
    # .batch_state.json으로 처리 완료 파일을 걸러내고 force_reingest를
    # 반영하므로(SPRINT22-A, tests/test_processing_upload.py로 검증됨),
    # 그 결과를 그대로 재사용해 대기열과 정의를 일치시킨다.
    candidate_files = _build_file_list(target_dir, effective_force_reingest)

    # [2026-07-21] 강제 재처리 문서 선택 기능 — "강제 재처리"/"전체
    # 재청킹"을 켜면 이미 처리된 문서까지 전부 대상이 되어 특정 문서만
    # 다시 처리하고 싶어도 방법이 없었다(사용자 보고). 강제 옵션이 켜진
    # 경우에만 멀티셀렉트를 보여주고, 꺼져 있으면(일반 신규 처리) 기존
    # 동작 그대로 전체를 처리한다 — 매번 선택을 강요하지 않는다.
    selected_names: Optional[List[str]] = None
    if effective_force_reingest and candidate_files:
        all_names = [f["name"] for f in candidate_files]
        selected_names = st.multiselect(
            "재처리할 문서 선택 (비워두면 전체)",
            options=all_names,
            default=all_names,
            key="force_reprocess_selection",
            help="강제 재처리/전체 재청킹 대상 문서를 좁힐 수 있습니다.",
        )

    file_list = _filter_selected_files(candidate_files, selected_names)
    pending_count = len(file_list)

    # Start processing button
    st.divider()

    if force_rechunk:
        st.warning("전체 재청킹이 켜져 있습니다 — 내용이 동일한 문서도 청킹을 처음부터 다시 실행합니다. 문서 수가 많으면 오래 걸릴 수 있습니다.")

    if pending_count == 0:
        st.info("처리할 문서가 없습니다.")
        st.button("🚀 문서 처리 시작", type="primary", use_container_width=True, disabled=True)
    else:
        st.caption(f"처리 가능: {pending_count}개 문서")

        if st.button("🚀 문서 처리 시작", type="primary", use_container_width=True):
            _execute_processing(file_list, chunk_size, overlap, use_ocr, effective_force_reingest, force_rechunk)


def _render_item_row(icon: str, name: str, detail: str, border_color: str, badge_bg: str, badge_fg: str, badge_text: str) -> None:
    """Shared row renderer for queue/history/failure lists — one file per line
    with a colored left border and a status badge."""
    html = f"""
    <div style="display: flex; align-items: center; padding: 8px 12px; border-left: 3px solid {border_color}; margin-bottom: 4px;">
        <span style="font-size: 16px; margin-right: 12px;">{icon}</span>
        <div style="flex: 1;">
            <div style="font-size: 13px; font-weight: 500; color: {THEME.TEXT_PRIMARY};">
                {name}
            </div>
            <div style="font-size: 11px; color: {THEME.TEXT_TERTIARY};">
                {detail}
            </div>
        </div>
        <span style="margin-left: 12px;">
            <span style="padding: 2px 8px; border-radius: 4px; background: {badge_bg}; color: {badge_fg}; font-size: 10px; font-weight: 600;">
                {badge_text}
            </span>
        </span>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def _render_processing_queue() -> None:
    """Render the processing queue."""
    store = StateStore()

    # Check for queued items
    raw_dir = Path(DEFAULT_RAW_DIR)
    if not raw_dir.exists():
        st.info("처리할 문서가 없습니다.")
        return

    files = list(raw_dir.iterdir())
    supported = [f for f in files if f.suffix.lower() in SUPPORTED_EXTS and f.is_file()]

    if not supported:
        st.info("지원되지 않는 파일 유형입니다. (PDF, TXT, MD, DOCX, EPUB, HTML, RTF)")
        return

    # 이미 처리된 파일(.batch_state.json)은 실제 처리 대상이 아니므로 대기열에서 제외 —
    # _build_file_list()의 skip 로직과 일치시켜 "대기열 N개 vs 처리할 파일 없음" 불일치 제거.
    state_file = Path(DEFAULT_OUTPUT_DIR) / ".batch_state.json"
    processed: set[str] = set()
    last_run_ts: Optional[datetime] = None
    if state_file.exists():
        try:
            state_data = json.loads(state_file.read_text(encoding="utf-8"))
            processed = set(state_data.get("processed", []))
            if state_data.get("timestamp"):
                last_run_ts = datetime.fromisoformat(state_data["timestamp"])
        except (json.JSONDecodeError, OSError, ValueError):
            pass

    queued = [f for f in supported if f.name not in processed]

    if not queued:
        st.info(f"대기열: 0개 (전체 {len(supported)}개 모두 처리 완료). "
                "재처리하려면 위의 문서 처리 영역에서 강제 재처리를 사용하세요.")
        return

    st.caption(f"대기열: {len(queued)}개 문서 (전체 {len(supported)}개 중 {len(processed & {f.name for f in supported})} 처리 완료)")

    # [SPRINT24-1] 실패한 파일은 mark_processed()에 도달하지 못해 항상
    # 대기열에 남아 자동 재시도되지만(core/processing.py 확인됨), 지금까지
    # 대기열 UI는 이를 신규 파일과 구분 없이 보여줬다. 최근 실패 사유를
    # source_file로 교차 매칭해 재시도 대상임을 표시한다(읽기 전용).
    failures = load_extraction_failures(DEFAULT_OUTPUT_DIR).get("failures", [])
    last_failure_by_file: dict[str, dict] = {}
    for fail in failures:  # append 순서(오래된→최신)이므로 뒤에서 덮어써 최신만 남김
        last_failure_by_file[fail.get("source_file", "")] = fail

    def _render_queue_item(f: Path) -> None:
        size_kb = f.stat().st_size / 1024 if f.exists() else 0
        prior_failure = last_failure_by_file.get(f.name)
        # 파일 mtime이 마지막 배치 처리 시각보다 늦으면 "그 이후에 새로
        # 들어온 파일" — 실패 이력이 없다면 "신규", 있다면(재시도 대상이
        # 우선) 재시도 예정으로 표시한다.
        is_new = last_run_ts is not None and datetime.fromtimestamp(f.stat().st_mtime) > last_run_ts

        if prior_failure:
            border_color = THEME.STATUS_WARNING
            badge_bg, badge_fg, badge_text = THEME.STATUS_WARNING_BG, THEME.STATUS_WARNING, "재시도 예정"
            detail = f"{size_kb:.0f} KB • 이전 실패: {prior_failure.get('reason', '?')}"
        elif is_new:
            border_color = THEME.STATUS_INFO
            badge_bg, badge_fg, badge_text = THEME.STATUS_INFO_BG, THEME.STATUS_INFO, "🆕 신규"
            detail = f"{size_kb:.0f} KB"
        else:
            border_color = THEME.BRAND_SECONDARY
            badge_bg, badge_fg, badge_text = THEME.STATUS_INFO_BG, THEME.STATUS_INFO, "대기 중"
            detail = f"{size_kb:.0f} KB"

        _render_item_row("📄", f.name, detail, border_color, badge_bg, badge_fg, badge_text)

    visible, rest = queued[:10], queued[10:]
    for f in visible:
        _render_queue_item(f)
    if rest:
        with st.expander(f"나머지 {len(rest)}개 더보기"):
            for f in rest:
                _render_queue_item(f)


def _render_processing_history() -> None:
    """Render the processing history.

    [버그 수정 2026-07-21] 이전에는 .md 파일 존재만으로 "완료"라고 표시했다
    (추출·정제 직후 생성됨). 그런데 대기열(_render_processing_queue)은
    .batch_state.json의 processed 목록(청킹+원본 복사까지 끝나야 mark_
    processed()로 기록됨, core/processing.py:732)을 기준으로 삼는다 —
    청킹 단계에서 멈춘 파일은 .md만 있고 processed에는 없어, 히스토리엔
    "완료"로, 대기열엔 "대기 중"으로 동시에 나타나는 모순이 있었다.
    make_safe_stem()으로 processed 파일명 -> .md stem을 정방향 매핑해
    실제 파이프라인 완료 여부로 상태를 나눈다."""
    output_dir = Path(DEFAULT_OUTPUT_DIR)

    if not output_dir.exists():
        st.info("처리 기록이 없습니다.")
        return

    md_files = list(output_dir.rglob("*.md"))
    if not md_files:
        st.info("처리 기록이 없습니다.")
        return

    completed_stems = {make_safe_stem(name) for name in get_processed_files(DEFAULT_OUTPUT_DIR)}

    # Show recent processing history (last 5)
    file_times = []
    for f in md_files:
        try:
            dt = datetime.fromtimestamp(f.stat().st_mtime)
            file_times.append((f, dt))
        except OSError:
            pass

    file_times.sort(key=lambda x: x[1], reverse=True)

    done_count = sum(1 for f, _ in file_times if f.stem in completed_stems)
    st.caption(f"전체 {len(file_times)}개 중 {done_count}개 완료")

    def _render_history_item(f: Path, dt: datetime) -> None:
        size_kb = f.stat().st_size / 1024 if f.exists() else 0
        detail = f"{dt.strftime('%Y-%m-%d %H:%M')} • {size_kb:.0f} KB"
        if f.stem in completed_stems:
            _render_item_row("✅", f.stem, detail, THEME.STATUS_SUCCESS, THEME.STATUS_SUCCESS_BG, THEME.STATUS_SUCCESS, "완료")
        else:
            detail += " • 청킹 미완료"
            _render_item_row("⏳", f.stem, detail, THEME.STATUS_WARNING, THEME.STATUS_WARNING_BG, THEME.STATUS_WARNING, "처리 중")

    visible, rest = file_times[:5], file_times[5:]
    for f, dt in visible:
        _render_history_item(f, dt)
    if rest:
        with st.expander(f"나머지 {len(rest)}개 더보기"):
            for f, dt in rest:
                _render_history_item(f, dt)


def _execute_processing(
    file_list: List[Dict[str, Any]],
    chunk_size: int,
    overlap: int,
    use_ocr: bool,
    force_reingest: bool,
    force_rechunk: bool = False,
) -> None:
    """Execute the document processing pipeline.

    [2026-07-21] file_list는 호출부(_render_ingestion_form)에서 이미
    _build_file_list() + _filter_selected_files()로 확정된 목록을
    그대로 받는다 — 여기서 target_dir을 다시 스캔하면 사용자가 고른
    문서 선택이 무시되므로 재빌드하지 않는다."""

    if not file_list:
        st.info("처리할 파일이 없습니다. (이미 처리되었거나 파일이 없는 경우)")
        return
    
    total_files = len(file_list)
    st.info(f"문서 처리가 시작되었습니다... ({total_files}개 파일)")
    
    # Create progress container
    progress_container = st.container()
    with progress_container:
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Define report callback for inline progress updates
        def report_callback(stage: str, message: str, progress: Optional[float] = None):
            if stage == "done":
                status_text.success(f"✅ {message}")
                progress_bar.progress(1.0)
            elif stage.startswith("extract"):
                status_text.info(f"📖 추출 중: {message}")
                p = progress or 0.2
                progress_bar.progress(p * total_files / total_files)
            elif stage == "chunk_done":
                status_text.info(f"✂️ 청킹 중: {message}")
            else:
                status_text.info(f"⏳ {message}")
        
        # Build processing pipeline components
        converter = build_converter(use_ocr=use_ocr)
        splitter = build_splitter(chunk_size=chunk_size, chunk_overlap=overlap)
        
        output_dir = DEFAULT_OUTPUT_DIR
        
        # Execute batch processing
        try:
            results = process_batch(
                file_list=file_list,
                converter=converter,
                splitter=splitter,
                output_dir=output_dir,
                chunk_size=chunk_size,
                chunk_overlap=overlap,
                report=report_callback,
                force_reingest=force_reingest,
                force_rechunk=force_rechunk,
            )
            
            # Summarize results
            success_count = sum(1 for r in results if r.get("success", False))
            skipped_count = sum(1 for r in results if r.get("skipped", False))
            fail_count = total_files - success_count - skipped_count
            
            st.success(f"처리 완료: {success_count}개 성공, {skipped_count}개 건너뜀, {fail_count}개 실패")

            # Show failed files
            if fail_count > 0:
                with st.expander("실패한 파일 보기"):
                    for r in results:
                        if not r.get("success", False):
                            logs = r.get("logs", [])
                            for log in logs:
                                msg = log.get("msg", "")
                                st.error(f"❌ {msg}")

            # [DBMA-SEARCH-INFRA-001 HQ 제안 ⑧ Background Index Builder]
            # reconcile_pending()을 여기서 직접 기다리는 대신(예전엔 이 한
            # 줄이 전체 재색인이 끝날 때까지 이 페이지를 블로킹했음), 백그라운드
            # 워커를 깨우기만 하고 바로 돌아온다 — "사용자는 기다리지 않는다".
            # 실제 색인은 core/background_index_builder.py의 데몬 스레드가
            # core/index_orchestrator.py::reconcile_pending()을 그대로 호출해
            # 수행한다(재구현 없음).
            get_shared_background_builder().trigger_now()
            st.info("📥 백그라운드에서 검색 색인을 갱신하고 있습니다 — 잠시 후 검색에 반영됩니다.")

            # Refresh the page state
            st.rerun()
            
        except Exception as e:
            logger.exception("Processing pipeline failed")
            st.error(f"처리 중 오류가 발생했습니다: {str(e)}")


def _render_recent_failures() -> None:
    """[SPRINT23] Surface core/extraction_failures.py's persisted log —
    read-only. document_id doesn't exist for these (pre-identity
    failures: extraction exception / empty extraction / empty cleaned
    text — SPRINT21-H-1), so they never showed up in "처리 기록" above,
    which only lists successfully-written {stem}.md files. Previously
    this data was written but never surfaced anywhere in the UI.
    """
    data = load_extraction_failures(DEFAULT_OUTPUT_DIR)
    failures = data.get("failures", [])

    if not failures:
        st.info("실패 기록이 없습니다.")
        return

    # record_extraction_failure() appends in chronological order and
    # failed_at has only second-level precision — sorting by that string
    # ties within the same second and can silently misorder a fast batch
    # (stable sort keeps original order on ties). Reversing the
    # already-chronological list is exact regardless of timestamp precision.
    recent = list(reversed(failures))[:10]
    st.caption(f"전체 {len(failures)}건 중 최근 {len(recent)}건")

    for f in recent:
        html = f"""
        <div style="display: flex; align-items: center; padding: 8px 12px; border-left: 3px solid {THEME.STATUS_ERROR}; margin-bottom: 4px;">
            <span style="font-size: 16px; margin-right: 12px;">⚠️</span>
            <div style="flex: 1;">
                <div style="font-size: 13px; font-weight: 500; color: {THEME.TEXT_PRIMARY};">
                    {f.get("source_file", "?")}
                </div>
                <div style="font-size: 11px; color: {THEME.TEXT_TERTIARY};">
                    {f.get("failed_at", "?")} • {_failure_label(f)}
                    {f" • 재시도 {f['retry_count']}회" if f.get("retry_count") else ""}
                </div>
            </div>
        </div>
        """
        st.markdown(html, unsafe_allow_html=True)
        st.caption(f"　　사유: {f.get('reason', '?')}")