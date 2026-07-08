"""DBMA Design System — Document Processing Page.

Document ingestion and processing workflow interface.
"""

from typing import Optional

import streamlit as st
from pathlib import Path

from ui.pages._base import BasePage
from ui.theme.colors import THEME
from ui.components.status import progress_indicator, status_badge
from ui.state.store import StateStore
from core.config import DEFAULT_RAW_DIR, DEFAULT_OUTPUT_DIR


def render_processing_page() -> None:
    """Render the DBMA Document Processing page."""
    page = BasePage(title="Document Processing", icon="📄")
    page.render_header()

    # ── Ingestion Form ─────────────────────────────────────────
    page.render_section("문서 처리", icon="📥")
    _render_ingestion_form()

    # ── Processing Queue ───────────────────────────────────────
    page.render_section("처리 대기열", icon="📋")
    _render_processing_queue()

    # ── Processing History ─────────────────────────────────────
    page.render_section("처리 기록", icon="📜")
    _render_processing_history()

    page.render_footer()


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
    col1, col2, col3 = st.columns(3)
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

    # Start processing button
    st.divider()
    if st.button("🚀 문서 처리 시작", type="primary", use_container_width=True):
        st.info("문서 처리가 시작되었습니다...")
        # TODO: trigger processing pipeline


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
    queued = [f for f in files if f.suffix.lower() in supported_exts]

    if not queued:
        st.info("지원되지 않는 파일 유형입니다. (PDF, TXT, MD, DOCX)")
        return

    st.caption(f"대기열: {len(queued)}개 문서")

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
    from datetime import datetime
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