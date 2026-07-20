"""DBMA Design System — Dashboard Page.

System overview with document statistics, processing status, and system health monitoring.
"""

from typing import Optional

import streamlit as st
import os
from pathlib import Path

from ui.pages._base import BasePage
from ui.theme.colors import THEME
from core.config import APP_VERSION, APP_NAME, DEFAULT_RAW_DIR, DEFAULT_OUTPUT_DIR, DEFAULT_EMBED_MODEL
from core.execution_context import ExecutionContext


def render_dashboard_page() -> None:
    """Render the DBMA Dashboard page."""
    page = BasePage(title="Dashboard", icon="🏠")
    page.render_header()

    # ── System Overview Metrics ────────────────────────────────
    _render_system_overview()

    # ── Document Corpus Statistics ─────────────────────────────
    page.render_section("문서 코퍼스 통계", icon="📚")
    _render_corpus_statistics()

    page.render_footer()


def _render_system_overview() -> None:
    """Render system overview metrics row.

    [design] Dashboard is the user-facing summary — "내 자료가 얼마나
    있고, 잘 돌아가는가" 한 줄. 파이프라인 단계별 %, 벡터DB/메모리 등
    개발자용 상세는 Monitor 페이지로 옮겼다(같은 정보를 두 곳에서 각각
    실데이터/가짜 데이터로 따로 보여주던 중복을 해소).
    """
    status_label, status_icon, status_color = _get_overall_status()
    metrics = [
        {"icon": "📄", "label": "전체 문서", "value": _count_documents(), "color": THEME.BRAND_PRIMARY},
        {"icon": "💾", "label": "코퍼스 크기", "value": _format_size(_get_corpus_size()), "color": THEME.STATUS_SUCCESS},
        {"icon": "🔄", "label": "마지막 처리", "value": _get_last_processed(), "color": THEME.STATUS_INFO},
        {"icon": status_icon, "label": "전체 상태", "value": status_label, "color": status_color},
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
        st.metric("지원 형식", "PDF/TXT/MD/DOCX/EPUB/HTML/RTF")
    with c4:
        st.metric("임베딩", DEFAULT_EMBED_MODEL)


def _get_overall_status() -> tuple[str, str, str]:
    """One-line health summary for the Dashboard's "전체 상태" card.

    Derived from the same ExecutionContext().get_pipeline_status() that
    Monitor's detailed per-stage view reads — Dashboard just collapses it
    to complete/in-progress instead of duplicating per-stage rendering.
    Stage-by-stage detail (%, vector DB, memory, etc.) lives on Monitor.

    Returns:
        (label, icon, color) for the metric card.
    """
    stages = ExecutionContext().get_pipeline_status()
    if stages and all(s.status == "complete" for s in stages):
        return "정상", "✅", THEME.STATUS_SUCCESS
    if any(s.status == "active" for s in stages):
        return "처리 중", "🔄", THEME.STATUS_INFO
    return "확인 필요", "⚠️", THEME.STATUS_WARNING


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
    """Get last processed timestamp from the identity registry (most recent
    last_processed_at across documents)."""
    from core.config import DEFAULT_REGISTRY_PATH
    from core.identity_registry import load_identity_registry

    registry = load_identity_registry(DEFAULT_REGISTRY_PATH)
    stamps = [
        doc.get("last_processed_at")
        for doc in registry.get("documents", {}).values()
        if doc.get("last_processed_at")
    ]
    if not stamps:
        return "N/A"
    return max(stamps)[:16].replace("T", " ")


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