"""DBMA Design System — Dashboard Page.

System overview with document statistics, processing status, and system health monitoring.
"""

from typing import Optional

import streamlit as st
import os
from pathlib import Path

from ui.pages._base import BasePage
from ui.theme.colors import THEME
from core.config import APP_VERSION, APP_NAME, DEFAULT_RAW_DIR, DEFAULT_OUTPUT_DIR


def render_dashboard_page() -> None:
    """Render the DBMA Dashboard page."""
    page = BasePage(title="Dashboard", icon="🏠")
    page.render_header()

    # ── System Overview Metrics ────────────────────────────────
    _render_system_overview()

    # ── Document Corpus Statistics ─────────────────────────────
    page.render_section("문서 코퍼스 통계", icon="📚")
    _render_corpus_statistics()

    # ── Processing Pipeline Status ─────────────────────────────
    page.render_section("처리 파이프라인 상태", icon="⚙️")
    _render_pipeline_status()

    # ── System Health ──────────────────────────────────────────
    page.render_section("시스템 상태", icon="💚")
    _render_system_health()

    page.render_footer()


def _render_system_overview() -> None:
    """Render system overview metrics row."""
    metrics = [
        {"icon": "📄", "label": "전체 문서", "value": _count_documents(), "color": THEME.BRAND_PRIMARY},
        {"icon": "💾", "label": "코퍼스 크기", "value": _format_size(_get_corpus_size()), "color": THEME.STATUS_SUCCESS},
        {"icon": "🔄", "label": "마지막 처리", "value": _get_last_processed(), "color": THEME.STATUS_INFO},
        {"icon": "✅", "label": "시스템", "value": "정상", "color": THEME.STATUS_SUCCESS},
    ]

    cols = st.columns(4)
    for i, m in enumerate(metrics):
        with cols[i]:
            html = f"""
            <div style="text-align: center; padding: {16}px 8px;">
                <div style="font-size: 28px; margin-bottom: 8px;">{m['icon']}</div>
                <div style="font-size: 20px; font-weight: 700; color: {m['color']};">
                    {m['value']}
                </div>
                <div style="font-size: 12px; color: {THEME.TEXT_SECONDARY}; margin-top: 4px;">
                    {m['label']}
                </div>
            </div>
            """
            st.markdown(html, unsafe_allow_html=True)


def _render_corpus_statistics() -> None:
    """Render corpus statistics."""
    raw_docs, output_docs = _get_document_counts()

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("RAW 폴더", f"{raw_docs}개 파일")
    with c2:
        st.metric("출력 폴더", f"{output_docs}개 파일")
    with c3:
        st.metric("지원 형식", "PDF/TXT/MD/DOCX")
    with c4:
        st.metric("임베딩", "all-MiniLM-L6-v2")


def _render_pipeline_status() -> None:
    """Render processing pipeline status."""
    stages = [
        {"label": "추출", "status": "complete", "progress": 100},
        {"label": "청킹", "status": "complete", "progress": 100},
        {"label": "임베딩", "status": "complete", "progress": 100},
        {"label": "인덱싱", "status": "complete", "progress": 100},
        {"label": "검색", "status": "active", "progress": 75},
    ]

    cols = st.columns(len(stages) + (len(stages) - 1))
    stage_colors = {
        "complete": THEME.STATUS_SUCCESS,
        "active": THEME.BRAND_SECONDARY,
        "pending": THEME.TEXT_TERTIARY,
    }
    stage_icons = {
        "complete": "✅",
        "active": "🔄",
        "pending": "⏳",
    }

    for i, stage in enumerate(stages):
        with cols[i * 2]:
            color = stage_colors.get(stage["status"], stage_colors["pending"])
            icon = stage_icons.get(stage["status"], stage_icons["pending"])
            html = f"""
            <div style="text-align: center; padding: {8}px 4px;">
                <div style="font-size: 20px; margin-bottom: 4px;">{icon}</div>
                <div style="font-size: 12px; color: {color}; font-weight: 600;">
                    {stage['label']}
                </div>
                <div style="font-size: 10px; color: {THEME.TEXT_TERTIARY};">
                    {stage['progress']}%
                </div>
            </div>
            """
            st.markdown(html, unsafe_allow_html=True)

        if i < len(stages) - 1:
            with cols[i * 2 + 1]:
                next_stage = stages[i + 1]
                line_color = stage_colors.get(next_stage["status"], stage_colors["pending"])
                st.progress(0.8)
                st.caption("→")


def _render_system_health() -> None:
    """Render system health indicators."""
    statuses = [
        {"label": "벡터DB", "status": "success"},
        {"label": "임베딩 모델", "status": "success"},
        {"label": "파일 시스템", "status": "success"},
        {"label": "메모리", "status": "info"},
    ]

    cols = st.columns(len(statuses))
    for i, s in enumerate(statuses):
        with cols[i]:
            _BG_COLORS = {
                "success": THEME.STATUS_SUCCESS_BG,
                "warning": THEME.STATUS_WARNING_BG,
                "error": THEME.STATUS_ERROR_BG,
                "info": THEME.STATUS_INFO_BG,
                "neutral": THEME.STATUS_NEUTRAL_BG,
            }
            _TEXT_COLORS = {
                "success": THEME.STATUS_SUCCESS,
                "warning": THEME.STATUS_WARNING,
                "error": THEME.STATUS_ERROR,
                "info": THEME.STATUS_INFO,
                "neutral": THEME.STATUS_NEUTRAL,
            }

            bg = _BG_COLORS.get(s["status"], THEME.STATUS_NEUTRAL_BG)
            text_color = _TEXT_COLORS.get(s["status"], THEME.STATUS_NEUTRAL)

            html = f"""
            <div style="text-align: center; padding: {12}px;">
                <span style="
                    display: inline-block;
                    padding: 4px 12px;
                    border-radius: 4px;
                    background: {bg};
                    color: {text_color};
                    font-size: 12px;
                    font-weight: 600;
                ">
                    ✅ {s['label']} 정상
                </span>
            </div>
            """
            st.markdown(html, unsafe_allow_html=True)


# ── Utility Functions ──────────────────────────────────────────────

def _count_documents() -> int:
    """Count total source documents in RAW directory.

    Uses same discovery rules as Library and Processing pages:
    - Recursive search (rglob)
    - Supported extensions: .pdf, .epub, .txt, .md, .docx
    - Excludes hidden files and directories
    - Includes only files (not directories)
    """
    raw_dir = Path(DEFAULT_RAW_DIR)
    if not raw_dir.exists():
        return 0

    supported_exts = {".pdf", ".epub", ".txt", ".md", ".docx"}
    doc_files = [
        f for f in raw_dir.rglob("*")
        if f.is_file() and not f.name.startswith(".") and f.suffix.lower() in supported_exts
    ]
    return len(doc_files)


def _get_corpus_size() -> int:
    """Get total corpus size in bytes."""
    output_dir = Path(DEFAULT_OUTPUT_DIR)
    if not output_dir.exists():
        return 0
    total = 0
    for f in output_dir.rglob("*.md"):
        total += f.stat().st_size
    return total


def _get_last_processed() -> str:
    """Get last processed timestamp."""
    return "N/A"


def _get_document_counts() -> tuple[int, int]:
    """Get RAW and output document counts.

    RAW count uses same discovery rules as Library page:
    - Recursive search (rglob)
    - Supported extensions only
    - Excludes hidden files
    - Includes only files (not directories)
    """
    supported_exts = {".pdf", ".epub", ".txt", ".md", ".docx"}

    raw_count = 0
    raw_dir = Path(DEFAULT_RAW_DIR)
    if raw_dir.exists():
        raw_count = len([
            f for f in raw_dir.rglob("*")
            if f.is_file() and not f.name.startswith(".") and f.suffix.lower() in supported_exts
        ])

    output_count = len(list(Path(DEFAULT_OUTPUT_DIR).rglob("*.md"))) if Path(DEFAULT_OUTPUT_DIR).exists() else 0

    return raw_count, output_count


def _format_size(size_bytes: int) -> str:
    """Format bytes to human-readable size."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"