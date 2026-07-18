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
from core.index_orchestrator import reconcile_pending
from core.processing import (
    build_converter,
    build_splitter,
    process_batch,
    get_processed_files,
)

logger = logging.getLogger(__name__)


def render_processing_page() -> None:
    """Render the DBMA Document Processing page."""
    page = BasePage(title="Document Processing", icon="📄")
    page.render_header()

    # ── Ingestion Form ─────────────────────────────────────────
    page.render_section("문書 처리", icon="📥")
    _render_ingestion_form()

    # ── Processing Queue ───────────────────────────────────────
    page.render_section("처리 대기열", icon="📋")
    _render_processing_queue()

    # ── Processing History ─────────────────────────────────────
    page.render_section("처리 기록", icon="📜")
    _render_processing_history()

    page.render_footer()


def _build_file_list(target_dir: str, force_reingest: bool) -> List[Dict[str, Any]]:
    """Build file list from target directory, respecting force_reingest flag."""
    raw_path = Path(target_dir)
    if not raw_path.exists():
        return []

    supported_exts = {".pdf", ".txt", ".md", ".docx"}
    files = []

    for f in sorted(raw_path.iterdir()):
        if f.suffix.lower() not in supported_exts:
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


def _render_ingestion_form() -> None:
    """Render the document ingestion form."""
    store = StateStore()

    c1, c2 = st.columns([1, 1])
    with c1:
        target_dir = st.text_input(
            "처리 대상 폴더",
            value=DEFAULT_RAW_DIR,
            key="processing_target",
        )
        store.set("processing_target", target_dir)

    with c2:
        chunk_size = st.number_input(
            "청크 크기 (문자)",
            min_value=256,
            max_value=8192,
            value=1000,
            step=256,
            key="chunk_size",
        )
        store.set("chunk_size", chunk_size)

    # Additional options
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        overlap = st.number_input(
            "오버랩 (문자)",
            min_value=0,
            max_value=500,
            value=200,
            step=50,
            key="chunk_overlap",
        )
    with col2:
        use_ocr = st.checkbox("OCR 사용", value=False, key="use_ocr")
    with col3:
        force_reingest = st.checkbox("강제 재처리", value=False, key="force_reingest")
    with col4:
        store.set("use_ocr", use_ocr)
        store.set("force_reingest", force_reingest)

    # Count pending files
    raw_path = Path(target_dir)
    supported_exts = {".pdf", ".txt", ".md", ".docx"}
    pending_count = 0
    if raw_path.exists():
        for f in raw_path.iterdir():
            if f.suffix.lower() in supported_exts and f.is_file():
                pending_count += 1

    # Start processing button
    st.divider()
    
    if pending_count == 0:
        st.info("처리할 문서가 없습니다.")
        st.button("🚀 문서 처리 시작", type="primary", use_container_width=True, disabled=True)
    else:
        st.caption(f"처리 가능: {pending_count}개 문서")
        
        if st.button("🚀 문서 처리 시작", type="primary", use_container_width=True):
            _execute_processing(target_dir, chunk_size, overlap, use_ocr, force_reingest)


def _render_processing_queue() -> None:
    """Render the processing queue."""
    store = StateStore()

    # Check for queued items
    raw_dir = Path(DEFAULT_RAW_DIR)
    if not raw_dir.exists():
        st.info("처리할 문서가 없습니다.")
        return

    files = list(raw_dir.iterdir())
    supported_exts = {".pdf", ".txt", ".md", ".docx"}
    supported = [f for f in files if f.suffix.lower() in supported_exts and f.is_file()]

    if not supported:
        st.info("지원되지 않는 파일 유형입니다. (PDF, TXT, MD, DOCX)")
        return

    # 이미 처리된 파일(.batch_state.json)은 실제 처리 대상이 아니므로 대기열에서 제외 —
    # _build_file_list()의 skip 로직과 일치시켜 "대기열 N개 vs 처리할 파일 없음" 불일치 제거.
    state_file = Path(DEFAULT_OUTPUT_DIR) / ".batch_state.json"
    processed: set[str] = set()
    if state_file.exists():
        try:
            processed = set(json.loads(state_file.read_text(encoding="utf-8")).get("processed", []))
        except (json.JSONDecodeError, OSError):
            pass

    queued = [f for f in supported if f.name not in processed]

    if not queued:
        st.info(f"대기열: 0개 (전체 {len(supported)}개 모두 처리 완료). "
                "재처리하려면 아래에서 강제 재처리를 사용하세요.")
        return

    st.caption(f"대기열: {len(queued)}개 문서 (전체 {len(supported)}개 중 {len(processed & {f.name for f in supported})} 처리 완료)")

    for i, f in enumerate(queued[:10]):  # Show max 10
        size_kb = f.stat().st_size / 1024 if f.exists() else 0
        html = f"""
        <div style="display: flex; align-items: center; padding: 8px 12px; border-left: 3px solid {THEME.BRAND_SECONDARY}; margin-bottom: 4px;">
            <span style="font-size: 16px; margin-right: 12px;">📄</span>
            <div style="flex: 1;">
                <div style="font-size: 13px; font-weight: 500; color: {THEME.TEXT_PRIMARY};">
                    {f.name}
                </div>
                <div style="font-size: 11px; color: {THEME.TEXT_TERTIARY};">
                    {size_kb:.0f} KB
                </div>
            </div>
            <span style="margin-left: 12px;">
                <span style="padding: 2px 8px; border-radius: 4px; background: {THEME.STATUS_INFO_BG}; color: {THEME.STATUS_INFO}; font-size: 10px; font-weight: 600;">
                    대기 중
                </span>
            </span>
        </div>
        """
        st.markdown(html, unsafe_allow_html=True)


def _render_processing_history() -> None:
    """Render the processing history."""
    output_dir = Path(DEFAULT_OUTPUT_DIR)

    if not output_dir.exists():
        st.info("처리 기록이 없습니다.")
        return

    md_files = list(output_dir.rglob("*.md"))
    if not md_files:
        st.info("처리 기록이 없습니다.")
        return

    # Show recent processing history (last 5)
    file_times = []
    for f in md_files:
        try:
            dt = datetime.fromtimestamp(f.stat().st_mtime)
            file_times.append((f, dt))
        except OSError:
            pass

    file_times.sort(key=lambda x: x[1], reverse=True)

    for f, dt in file_times[:5]:
        size_kb = f.stat().st_size / 1024 if f.exists() else 0
        html = f"""
        <div style="display: flex; align-items: center; padding: 8px 12px; border-left: 3px solid {THEME.STATUS_SUCCESS}; margin-bottom: 4px;">
            <span style="font-size: 16px; margin-right: 12px;">✅</span>
            <div style="flex: 1;">
                <div style="font-size: 13px; font-weight: 500; color: {THEME.TEXT_PRIMARY};">
                    {f.stem}
                </div>
                <div style="font-size: 11px; color: {THEME.TEXT_TERTIARY};">
                    {dt.strftime("%Y-%m-%d %H:%M")} • {size_kb:.0f} KB
                </div>
            </div>
            <span style="margin-left: 12px;">
                <span style="padding: 2px 8px; border-radius: 4px; background: {THEME.STATUS_SUCCESS_BG}; color: {THEME.STATUS_SUCCESS}; font-size: 10px; font-weight: 600;">
                    완료
                </span>
            </span>
        </div>
        """
        st.markdown(html, unsafe_allow_html=True)


def _execute_processing(
    target_dir: str,
    chunk_size: int,
    overlap: int,
    use_ocr: bool,
    force_reingest: bool,
) -> None:
    """Execute the document processing pipeline."""
    
    # Build file list
    file_list = _build_file_list(target_dir, force_reingest)
    
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

            # [SPRINT21-F-1] Processing → TSU Reconciliation, one click.
            # reconcile_pending()은 무예외(never raises) — pending 문서가
            # 없거나 개별 문서가 실패해도 결과 dict만 반환한다(SPRINT21-B).
            reconcile_result = reconcile_pending(output_dir)
            if reconcile_result["reconciled"] > 0:
                st.success(f"색인 갱신: {reconcile_result['reconciled']}개 문서 검색 반영 완료")
            if reconcile_result["failed"]:
                with st.expander(f"색인 실패 {len(reconcile_result['failed'])}건 보기"):
                    for f in reconcile_result["failed"]:
                        st.error(f"❌ {f['document_id']}: {f['error']}")

            # Refresh the page state
            st.rerun()
            
        except Exception as e:
            logger.exception("Processing pipeline failed")
            st.error(f"처리 중 오류가 발생했습니다: {str(e)}")