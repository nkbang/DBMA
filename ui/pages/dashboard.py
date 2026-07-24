"""DBMA Design System — Dashboard Page.

System overview with document statistics, processing status, and system health monitoring.
"""

from typing import Optional

import streamlit as st
import os
from pathlib import Path

from ui.pages._base import BasePage
from ui.theme.colors import THEME
from core.config import APP_VERSION, APP_NAME, DEFAULT_RAW_DIR
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
    # [버그 수정 2026-07-21] "보유 문서"(RAW 폴더 파일 수)와 "정리된
    # 자료"는 서로 다른 걸 재는 지표다 — 처리된 원본은 RAW에서 지워지는
    # 경우가 많아 RAW 카운트가 총 보유량을 반영하지 않는다(사용자 보고:
    # "61권 vs 79개" 불일치). RAW는 계산 로직 그대로 두고 라벨만 정확하게.
    #
    # [버그 수정 2026-07-22] "정리된 자료"는 사용자 재보고("74개인데
    # 유형별 문서는 124개") 원인 — 이전엔 output/ 폴더의 .md 파일 수를
    # 세었고, 아래 유형별 문서 카드는 registry 전체 항목 수(superseded/
    # 미완료 포함)를 세어서 서로 다른 모집단이었다. 이제 둘 다
    # _effective_documents()로 걸러낸 "실질적으로 유효한 등록 문서"
    # 하나의 집합을 공유해 두 숫자가 항상 일치하도록 통일한다.
    #
    # [버그 수정 2026-07-24] "RAW 대기 문서"라는 라벨이 "미처리"를
    # 뜻하는 것처럼 읽히지만 실제로는 처리 여부와 무관하게 RAW 폴더에
    # 물리적으로 있는 파일 수였다(사용자 보고: 69권이 실제로는 전부
    # 처리 완료 상태). 처리 완료/미처리를 나눠서 보여준다.
    effective_docs = _get_effective_documents()
    raw_breakdown = _get_raw_processing_breakdown()

    c1, c2 = st.columns(2)
    with c1:
        st.metric(
            "RAW 폴더 파일",
            f"{raw_breakdown['total']}권",
            help="data/RAW 폴더에 현재 남아있는 파일 수 — 처리 여부와 무관합니다. 처리된 원본이 삭제되지 않고 RAW에 남아있는 경우가 흔해, 아래 처리 완료/미처리 구분을 함께 보세요.",
        )
        st.caption(
            f"✅ 처리 완료 {raw_breakdown['processed']}권 · "
            f"⏳ 미처리 {raw_breakdown['unprocessed']}권"
        )
    with c2:
        st.metric("정리된 자료", f"{len(effective_docs)}개 문서", help="registry에 등록된 문서 중 청킹 완료(chunk_count>0)·처리 성공(ingest_status=PROCESSED)·최신본(superseded_by 없음)만 센 수 — 아래 '유형별 문서'와 항상 같은 모집단입니다.")


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
    - Supported extensions: core.config.SUPPORTED_EXTENSIONS
    - Excludes hidden files and directories
    - Includes only files (not directories)
    """
    from core.config import SUPPORTED_EXTENSIONS

    raw_dir = Path(DEFAULT_RAW_DIR)
    if not raw_dir.exists():
        return 0

    doc_files = [
        f for f in raw_dir.rglob("*")
        if f.is_file() and not f.name.startswith(".") and f.suffix.lower() in SUPPORTED_EXTENSIONS
    ]
    return len(doc_files)


def _get_raw_processing_breakdown() -> dict:
    """[버그 수정 2026-07-24] "RAW 대기 문서"라는 이름과 달리 _count_
    documents()는 처리 여부와 무관하게 RAW 폴더에 물리적으로 있는 파일
    수만 센다 — 처리된 원본이 삭제되지 않고 RAW에 남아있는 경우가 흔해
    "대기 중"이라는 라벨이 오해를 준다(사용자 보고, 2026-07-24: 69권이
    전부 이미 처리 완료 상태였음). RAW 파일명을 TSU 데이터셋의
    source_file 집합과 대조해 실제 처리 완료/미처리를 구분한다.

    RetrievalEngine 전체를 띄우지 않고 TSU JSONL을 직접 스트리밍해
    source_file만 모은다 — Dashboard 렌더마다 52,064건 전체를 메모리에
    올리는 무거운 경로를 피하기 위함."""
    import json
    from core.config import DEFAULT_TSU_DATASET_PATH, SUPPORTED_EXTENSIONS

    raw_dir = Path(DEFAULT_RAW_DIR)
    if not raw_dir.exists():
        return {"total": 0, "processed": 0, "unprocessed": 0}

    raw_files = {
        f.name for f in raw_dir.rglob("*")
        if f.is_file() and not f.name.startswith(".") and f.suffix.lower() in SUPPORTED_EXTENSIONS
    }

    tsu_sources: set[str] = set()
    tsu_path = Path(DEFAULT_TSU_DATASET_PATH)
    if tsu_path.exists():
        with open(tsu_path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("$"):
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                source_file = rec.get("source_file")
                if source_file:
                    tsu_sources.add(source_file)

    processed = len(raw_files & tsu_sources)
    total = len(raw_files)
    return {"total": total, "processed": processed, "unprocessed": total - processed}


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


def _get_effective_documents() -> dict:
    """registry의 전체 문서 중 "실질적으로 유효한" 것만 걸러 반환한다.

    [버그 수정 2026-07-22] registry["documents"]는 실패/중단된 처리
    시도(ingest_status FAILED/ABANDONED)와 새 버전으로 대체된 옛
    항목(superseded_by가 set된 것)을 삭제하지 않고 그대로 쌓아두므로,
    이 필터 없이 len(registry["documents"])를 그대로 쓰면 대시보드의
    "정리된 자료"·"유형별 문서" 두 카드가 서로 다른 필터를 적용해 숫자가
    어긋난다(사용자 보고: 74 vs 124). 두 카드가 항상 이 함수 하나를
    공유하도록 해서 재발을 막는다.

    필터 기준:
      - chunk_count > 0            (청킹까지 실제로 완료된 문서만)
      - ingest_status == "PROCESSED" (실패/중단된 시도 제외; 필드가
        없는 구버전 레코드는 register_document()의 기본값과 동일하게
        "PROCESSED"로 간주 — core/identity_registry.py:275)
      - superseded_by is None       (대체된 옛 버전 제외, 최신본만)
    """
    from core.config import DEFAULT_REGISTRY_PATH
    from core.identity_registry import load_identity_registry

    registry = load_identity_registry(DEFAULT_REGISTRY_PATH)
    docs = registry.get("documents", {})
    return {
        doc_id: doc
        for doc_id, doc in docs.items()
        if doc.get("chunk_count", 0) > 0
        and doc.get("ingest_status", "PROCESSED") == "PROCESSED"
        and doc.get("superseded_by") is None
    }


# ── Document Type (doc_type) Summary & Manual Labeling ──────────────

_DOC_TYPE_ORDER = ["주석", "설교", "사전", "논문", "기타"]
_DOC_TYPE_ICONS = {
    "주석": "📖",
    "설교": "🎤",
    "사전": "📚",
    "논문": "📜",
    "기타": "📁",
}
# 유형별 수량사 — 책 형태 자료는 "권", 낱건 자료는 "건"으로 구분.
_DOC_TYPE_UNITS = {
    "주석": "권",
    "설교": "건",
    "사전": "권",
    "논문": "건",
    "기타": "권",
}


def _render_doc_type_summary() -> None:
    """Show doc_type distribution from registry and allow manual labeling.

    [버그 수정 2026-07-22] "정리된 자료" 카드와 동일한 _get_effective_documents()
    집합을 쓴다 — 이전엔 여기서 registry 전체(superseded/실패 포함)를
    분모로 삼아 "정리된 자료" 카드와 항상 어긋났다."""
    docs = _get_effective_documents()
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
            st.metric(f"{icon} {doc_type}", f"{counts[doc_type]}{_DOC_TYPE_UNITS.get(doc_type, '개')}")

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
