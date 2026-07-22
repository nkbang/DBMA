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
from core.execution_context import ExecutionContext


def render_dashboard_page() -> None:
    """Render the DBMA Dashboard page.

    [design] User-convenience redesign — Dashboard's job is "지금 바로
    쓸 수 있는가" and "다음에 뭘 누르면 되는가", not a stats readout.
    파이프라인 %, 벡터DB/메모리 등 개발자용 상세는 Monitor로 옮겨져 있다
    (같은 정보를 두 곳에서 실데이터/가짜 데이터로 중복 보여주던 문제 해소).
    """
    page = BasePage(title="Dashboard", icon="🏠")
    page.render_header()

    _render_status_banner()
    _render_quick_actions()

    st.markdown(f"<div style='font-size: 13px; color: {THEME.TEXT_SECONDARY}; margin: 1.5rem 0 0.5rem;'>내 서재</div>", unsafe_allow_html=True)
    _render_library_summary()
    _render_doc_type_summary()

    page.render_footer()


def _go_to(page_name: str) -> None:
    """on_click callback for quick-action buttons — see ui/app.py's
    nav radio (key="nav_page"), which reads this on the next rerun."""
    st.session_state["nav_page"] = page_name


def _render_status_banner() -> None:
    """One glance: can I use this right now, and what's in it."""
    status_label, status_icon, status_color, status_bg = _get_overall_status()
    raw_docs = _count_documents()
    last_processed = _get_last_processed()

    headline = "지금 바로 질문할 수 있어요" if status_label == "정상" else status_label
    html = f"""
    <div style="background: {status_bg}; border-radius: 12px; padding: 14px 18px; display: flex; align-items: center; gap: 10px;">
        <span style="font-size: 20px;">{status_icon}</span>
        <div>
            <div style="font-weight: 700; font-size: 15px; color: {status_color};">{headline}</div>
            <div style="font-size: 12px; color: {status_color};">문서 {raw_docs}권 · 마지막 업데이트 {last_processed}</div>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def _render_quick_actions() -> None:
    """Jump straight to the three things a user actually comes here to do."""
    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.button("💬 질문하기", use_container_width=True, on_click=_go_to, args=("Chat",))
    with c2:
        st.button("🔍 자료 검색", use_container_width=True, on_click=_go_to, args=("Research",))
    with c3:
        st.button("📤 문서 추가", use_container_width=True, on_click=_go_to, args=("Processing",))


def _render_library_summary() -> None:
    """Collapsed "내 서재" summary — RAW/출력/지원형식/임베딩 세부는
    개발자용 정보라 Monitor·Processing으로 이미 옮겨져 있다."""
    raw_docs, output_docs = _get_document_counts()

    c1, c2 = st.columns(2)
    with c1:
        st.metric("보유 문서", f"{raw_docs}권")
    with c2:
        st.metric("정리된 자료", f"{output_docs}개 문서")


def _get_overall_status() -> tuple[str, str, str, str]:
    """One-line health summary for the Dashboard's status banner.

    Derived from the same ExecutionContext().get_pipeline_status() that
    Monitor's detailed per-stage view reads — Dashboard just collapses it
    to complete/in-progress instead of duplicating per-stage rendering.
    Stage-by-stage detail (%, vector DB, memory, etc.) lives on Monitor.

    Returns:
        (label, icon, text_color, bg_color).
    """
    stages = ExecutionContext().get_pipeline_status()
    if stages and all(s.status == "complete" for s in stages):
        return "정상", "✅", THEME.STATUS_SUCCESS, THEME.STATUS_SUCCESS_BG
    if any(s.status == "active" for s in stages):
        return "처리 중", "🔄", THEME.STATUS_INFO, THEME.STATUS_INFO_BG
    return "확인 필요", "⚠️", THEME.STATUS_WARNING, THEME.STATUS_WARNING_BG


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


# ── Document Type (doc_type) Summary & Manual Labeling ──────────────

_DOC_TYPE_ORDER = ["주석", "설교", "사전", "논문", "기타"]
_DOC_TYPE_ICONS = {
    "주석": "📖",
    "설교": "🎤",
    "사전": "📚",
    "논문": "📜",
    "기타": "📁",
}


def _render_doc_type_summary() -> None:
    """Show doc_type distribution from registry and allow manual labeling."""
    from core.config import DEFAULT_REGISTRY_PATH
    from core.identity_registry import load_identity_registry

    registry = load_identity_registry(DEFAULT_REGISTRY_PATH)
    docs = registry.get("documents", {})
    if not docs:
        return

    # Count by type
    counts: dict[str, int] = {t: 0 for t in _DOC_TYPE_ORDER}
    untyped_ids: list[str] = []
    for doc in docs.values():
        dt = doc.get("doc_type")
        if dt and dt in counts:
            counts[dt] += 1
        else:
            untyped_ids.append(doc.get("document_id", ""))

    total = len(docs)
    labeled = total - len(untyped_ids)

    st.markdown(
        f"<div style='font-size: 12px; color: {THEME.TEXT_SECONDARY}; margin-top: 0.5rem;'>유형별 문서 ({labeled}/{total}개 라벨링됨)</div>",
        unsafe_allow_html=True,
    )

    # Display as small metric cards
    cols = st.columns(len(_DOC_TYPE_ORDER))
    for i, doc_type in enumerate(_DOC_TYPE_ORDER):
        with cols[i]:
            icon = _DOC_TYPE_ICONS.get(doc_type, "📁")
            st.metric(f"{icon} {doc_type}", f"{counts[doc_type]}개")

    # Manual labeling section for untyped documents (one row per document)
    if untyped_ids:
        st.markdown(f"<div style='margin-top: 1rem; font-size: 13px;'>미라벨링 문서 ({len(untyped_ids)}개)</div>", unsafe_allow_html=True)
        _render_manual_labeler(docs, untyped_ids)


def _render_manual_labeler(docs: dict, untyped_ids: list[str]) -> None:
    """Allow user to assign doc_type to each untyped document.
    
    Each document gets its own row with a type selector and save button.
    After saving, the document disappears from the list on rerun.
    """
    for target_id in untyped_ids:
        source_file = docs.get(target_id, {}).get("source_file", target_id)
        
        # Only show if this document is still untyped (defensive — should match untyped_ids)
        current_type = docs.get(target_id, {}).get("doc_type")
        if current_type and current_type in _DOC_TYPE_ORDER:
            continue  # Already labeled — skip
        
        col_doc, col_type, col_save = st.columns([3, 2, 1])
        
        with col_doc:
            st.markdown(f"**{source_file}**")
        
        with col_type:
            current_val = current_type if current_type else _DOC_TYPE_ORDER[0]
            chosen = st.selectbox(
                "유형",
                options=_DOC_TYPE_ORDER,
                index=_DOC_TYPE_ORDER.index(current_val) if current_val in _DOC_TYPE_ORDER else 0,
                key=f"_dt_label_{target_id}",
                format_func=lambda x: f"{_DOC_TYPE_ICONS.get(x, '📁')} {x}",
                label_visibility="collapsed",
            )
        
        with col_save:
            if st.button("저장", key=f"_dt_save_{target_id}", type="primary"):
                _save_doc_type(target_id, chosen)


def _save_doc_type(doc_id: str, doc_type: str) -> None:
    """Save doc_type to registry and persist."""
    from core.config import DEFAULT_REGISTRY_PATH
    from core.identity_registry import load_identity_registry, save_identity_registry

    registry = load_identity_registry(DEFAULT_REGISTRY_PATH)
    if doc_id in registry.get("documents", {}):
        registry["documents"][doc_id]["doc_type"] = doc_type
        registry["updated_at"] = __import__("datetime").datetime.now().isoformat(timespec="seconds")
        if save_identity_registry(registry, DEFAULT_REGISTRY_PATH):
            st.success(f"{doc_id[:8]}... → {doc_type} 저장 완료")
            st.rerun()
        else:
            st.error("저장에 실패했습니다.")
    else:
        st.error("문서를 찾을 수 없습니다.")
