"""DBMA Design System — Library Workspace Page.

Document library browsing, search, and management interface.
"""

import json
import unicodedata
from datetime import datetime
from typing import Optional

import pandas as pd
import streamlit as st
from pathlib import Path

from ui.pages._base import BasePage
from ui.theme.colors import THEME
from ui.components.tables import document_table, search_results_table
from ui.state.store import StateStore
from core.config import DEFAULT_RAW_DIR, DEFAULT_OUTPUT_DIR, DEFAULT_REGISTRY_PATH
from core.identity_registry import (
    load_identity_registry,
    save_identity_registry,
    find_by_source_file,
    get_supersession_chain,
    exclude_document,
    unexclude_document,
)
from core.index_orchestrator import exclude_document_from_index
from core.extraction_failures import load_extraction_failures
from core.chunking_optimizer import optimize_chunks
from core.utils import make_safe_stem


def _apply_library_styles() -> None:
    """자료 찾기(검색 결과) Stitch 화면 스타일 — 카드형 결과 목록, 타입 배지."""
    st.markdown(
        f"""
        <style>
        div[data-testid="stTextInput"] input {{
            border-radius: 999px !important;
            border-color: {THEME.BORDER_MEDIUM} !important;
        }}
        .lib-badge {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 10px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            background: {THEME.BRAND_SECONDARY}22;
            color: {THEME.BRAND_SECONDARY};
        }}
        .lib-badge.selected {{
            background: {THEME.BRAND_PRIMARY};
            color: #ffffff;
        }}
        .lib-card {{
            background: {THEME.BG_SURFACE};
            border: 1px solid {THEME.BORDER_LIGHT};
            border-radius: 8px;
            padding: 16px 20px;
            margin-bottom: 10px;
        }}
        .lib-card.selected {{
            border-color: {THEME.BRAND_PRIMARY};
        }}
        .lib-card .lib-title {{
            font-weight: 600;
            color: {THEME.TEXT_PRIMARY};
            margin: 8px 0 4px;
        }}
        .lib-card .lib-meta {{
            font-size: 12px;
            color: {THEME.TEXT_TERTIARY};
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_library_page() -> None:
    """Render the DBMA Library workspace page."""
    _apply_library_styles()
    page = BasePage(title="Library", icon="🔍")
    page.render_header()

    # ── Search Bar ─────────────────────────────────────────────
    _render_search_bar()

    # ── Document Collection ────────────────────────────────────
    page.render_section("문서 컬렉션", icon="📁")
    _render_document_collection()

    # ── Document Detail Panel ──────────────────────────────────
    page.render_section("문서 상세", icon="📋")
    _render_document_detail_panel()

    page.render_footer()


def _render_search_bar() -> None:
    """Render the global document search bar."""
    store = StateStore()

    query = st.text_input(
        "🔍 문서 검색",
        placeholder="문서 제목, 메타데이터 또는 내용으로 검색...",
        key="library_search",
        help="문서 이름, 타입, 메타데이터로 필터링합니다.",
    )
    if query:
        store.set("library_search_query", query)

     # Filter options
    c1, c2 = st.columns(2)
    with c1:
         file_type = st.selectbox(
             "파일 유형",
             options=["all", "pdf", "txt", "md", "docx", "epub", "html", "htm", "rtf"],
             key="library_file_type",
         )
    with c2:
        sort_by = st.selectbox(
            "정렬 기준",
            options=["name", "date", "size"],
            key="library_sort_by",
        )


# Default page size for Library pagination
_DEFAULT_PAGE_SIZE = 20


def _render_document_collection() -> None:
    """Render the document collection table with single-click selection and pagination."""
    all_documents = _get_documents_list()

    if not all_documents:
        st.info("📂 문서가 없습니다. RAW 폴더에 문서를 추가하세요.")
        return

    # Read file type filter from session state
    file_type = st.session_state.get("library_file_type", "all")

    # Apply extension filter when not "all"
    if file_type and file_type != "all":
        ext_key = f".{file_type.lower()}"
        filtered = [d for d in all_documents if d.get("type", "").lower() == file_type.lower()]
        documents = filtered
    else:
        documents = all_documents

    total_count = len(all_documents)
    shown_total_before_search = len(documents)

    # ── Search Query Filtering (FAT-HUMAN-008 + PT-SEARCH-001 Unicode NFC fix) ──
    search_query = st.session_state.get("library_search", "").strip()
    if search_query:
        # Normalize query to NFC to match macOS NFD filenames consistently
        query_normalized = unicodedata.normalize("NFC", search_query).lower()
        documents = [
            d for d in documents
            if any(
                query_normalized in unicodedata.normalize("NFC", str(d.get(k, ""))).lower()
                for k in ("title", "type", "path", "modified")
            )
        ]
    else:
        documents = list(documents)  # shallow copy

    shown_total = len(documents)

    # Display count (showing X of Y)
    if file_type != "all" and search_query:
        st.caption(f"{shown_total}개 문서 표시 (유형 {file_type}, 검색 \"{search_query}\", 총 {total_count}개 중)")
    elif file_type != "all":
        st.caption(f"{shown_total}개 문서 표시 (총 {total_count}개 중)")
    elif search_query:
        st.caption(f"\"{search_query}\" 검색 결과: {shown_total}개 문서 (총 {total_count}개 중)")
    else:
        st.caption(f"총 {shown_total}개의 문서")

    # Reset page back to 1 when filters change (new results may have fewer pages)
    if "library_current_page" not in st.session_state:
        st.session_state["library_current_page"] = 1

    # ── Pagination ────────────────────────────────────────────
    page_size = _DEFAULT_PAGE_SIZE
    total_pages = max(1, (shown_total + page_size - 1) // page_size)

    # Read current page from session state (default 1)
    if "library_current_page" not in st.session_state:
        st.session_state["library_current_page"] = 1
    current_page = st.session_state["library_current_page"]

    # Clamp page to valid range
    if current_page < 1:
        current_page = 1
        st.session_state["library_current_page"] = 1
    if current_page > total_pages:
        current_page = total_pages
        st.session_state["library_current_page"] = total_pages

    # Slice documents for current page
    start_idx = (current_page - 1) * page_size
    end_idx = min(start_idx + page_size, shown_total)
    paginated_docs = documents[start_idx:end_idx]

    # Render pagination controls (only when there are multiple pages)
    if total_pages > 1:
        _render_pagination_controls(current_page, total_pages, shown_total, page_size)

    # Render document table with selection buttons
    _render_document_rows(paginated_docs)


def _render_document_detail_panel() -> None:
    """Render the document detail inspection panel.
    
    Reads selected document from StateStore("library_selected_doc").
    No separate selectbox required — selection comes from Document Collection.
    """
    store = StateStore()
    selected_doc = store.get("library_selected_doc")

    if selected_doc is None:
        st.caption("📁 문서 컬렉션에서 문서를 선택하여 세부 정보를 확인하세요.")
        return

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**제목:** {selected_doc.get('title', 'N/A')}")
        st.markdown(f"**유형:** {selected_doc.get('type', 'N/A')}")
        st.markdown(f"**크기:** {selected_doc.get('size', 'N/A')}")
    with col2:
        st.markdown(f"**경로:** {selected_doc.get('path', 'N/A')}")
        st.markdown(f"**수정일:** {selected_doc.get('modified', 'N/A')}")

    # ── Registry Metadata Edit (SPRINT17-Phase5-C2 M2-b) ────────
    # Only shown once the selected raw file has been processed into a
    # registry record — matches by filename (source_file), same identifier
    # core/processing.py stores. Manual fallback for documents where
    # automatic extraction (PDF docinfo/DOCX core_properties) is missing
    # or wrong.
    _render_metadata_edit_form(selected_doc.get("title", ""))

    # ── 처리 제외 (exclude) ──────────────────────────────────────
    _render_exclude_section(selected_doc.get("title", ""))

    # ── Provenance: version history + failure history (SPRINT24-2) ──
    _render_provenance_section(selected_doc.get("title", ""))

    # ── Chunk Preview (RAGFlow-style on-demand chunking preview) ────
    _render_chunk_preview_section(selected_doc.get("title", ""), selected_doc.get("type", ""))

    # Add clear selection button — uses on_click callback for full page sync
    st.button(
        "✕ 선택 해제",
        key="clear_selection_btn",
        type="secondary",
        use_container_width=True,
        on_click=_clear_document_selection,
    )


def _registry_path() -> Path:
    return Path(DEFAULT_REGISTRY_PATH)


def _find_registry_record(source_filename: str) -> "tuple[Optional[str], Optional[dict]]":
    """Find the registry record whose source_file matches the given filename.

    Returns (document_id, record) or (None, None) if not found/not yet processed.
    """
    registry_path = _registry_path()
    if not registry_path.exists():
        return None, None
    registry = load_identity_registry(str(registry_path))
    for doc_id, record in registry.get("documents", {}).items():
        if record.get("source_file") == source_filename:
            return doc_id, record
    return None, None


def _render_provenance_section(source_filename: str) -> None:
    """[SPRINT24-2] Read-only join of this filename's version history
    (documents.json, via supersedes/superseded_by) and failure history
    (extraction_failures.json). The two logs stay decoupled at the data
    layer (SPRINT21-H-1 design) — this joins them only for display, by
    source_file, without introducing a new authority or schema.
    """
    if not source_filename:
        return

    registry_path = _registry_path()
    chain: list[dict] = []
    if registry_path.exists():
        registry = load_identity_registry(str(registry_path))
        current = find_by_source_file(registry, source_filename)
        if current is not None:
            chain = get_supersession_chain(registry, current["document_id"])

    failures = [
        f for f in load_extraction_failures(DEFAULT_OUTPUT_DIR).get("failures", [])
        if f.get("source_file") == source_filename
    ]

    if not chain and not failures:
        return  # nothing to show — avoid an empty "이력" expander for untouched files

    with st.expander("🕓 이력 (버전 / 실패 기록)", expanded=False):
        if chain:
            st.caption(f"버전 {len(chain)}개")
            for record in chain:
                status = "현재" if record.get("superseded_by") is None else "이전 버전(대체됨)"
                st.markdown(
                    f"- `{record.get('document_id', '?')[:16]}...` — {status}, "
                    f"pipeline_state={record.get('pipeline_state', '?')}, "
                    f"chunk_count={record.get('chunk_count', '?')}"
                )
        if failures:
            st.caption(f"실패 기록 {len(failures)}건")
            for f in reversed(failures):  # most recent first (append-order log)
                st.markdown(f"- {f.get('failed_at', '?')} • {f.get('stage', '?')} — {f.get('reason', '?')}")


def _render_metadata_edit_form(source_filename: str) -> None:
    """Render an editable title/author/chapter/page form for a processed
    document and persist edits back to the identity registry on save.
    """
    document_id, record = _find_registry_record(source_filename)
    if document_id is None:
        st.caption("ℹ️ 아직 처리되지 않은 문서입니다 — 메타데이터 수정은 처리 완료 후 가능합니다.")
        return

    with st.expander("📝 문서 메타데이터 수정 (title / author / chapter / page)", expanded=False):
        with st.form(key=f"metadata_edit_form_{document_id}"):
            new_title = st.text_input("제목 (title)", value=record.get("title") or "")
            new_author = st.text_input("저자 (author)", value=record.get("author") or "")
            c1, c2 = st.columns(2)
            with c1:
                chapter_str = st.text_input("장 (chapter)", value=str(record.get("chapter")) if record.get("chapter") is not None else "")
            with c2:
                page_str = st.text_input("페이지 (page)", value=str(record.get("page")) if record.get("page") is not None else "")
            submitted = st.form_submit_button("저장", use_container_width=True)

        if submitted:
            registry_path = _registry_path()
            registry = load_identity_registry(str(registry_path))
            target = registry.get("documents", {}).get(document_id)
            if target is None:
                st.error("저장 실패: registry에서 문서를 다시 찾지 못했습니다.")
                return
            target["title"] = new_title.strip() or None
            target["author"] = new_author.strip() or None
            try:
                target["chapter"] = int(chapter_str) if chapter_str.strip() else None
            except ValueError:
                st.error("장(chapter)은 숫자여야 합니다.")
                return
            try:
                target["page"] = int(page_str) if page_str.strip() else None
            except ValueError:
                st.error("페이지(page)는 숫자여야 합니다.")
                return
            if save_identity_registry(registry, str(registry_path)):
                st.success("저장되었습니다.")
                st.rerun()
            else:
                st.error("registry 저장에 실패했습니다.")


def _render_exclude_section(source_filename: str) -> None:
    """처리 제외(exclude) 토글 UI. RAW 원본은 건드리지 않는다.

    제외 시: registry ingest_status를 EXCLUDED로 표시하고, TSU 레코드/청크
    파일을 backups/excluded_documents_{date}/로 이동해 검색 대상에서 뺀다
    (core/index_orchestrator.py::exclude_document_from_index()).
    재포함 시: ingest_status만 PROCESSED로 되돌린다 — 검색되게 하려면
    별도로 재처리(재색인)가 필요하다는 점을 안내한다.
    """
    document_id, record = _find_registry_record(source_filename)
    if document_id is None:
        return  # 아직 처리되지 않은 문서 — 제외할 대상 자체가 없음

    is_excluded = record.get("ingest_status") == "EXCLUDED"

    with st.expander("🚫 처리 제외 관리", expanded=is_excluded):
        if is_excluded:
            st.warning(
                f"이 문서는 제외 상태입니다 (사유: {record.get('exclude_reason') or '-'}, "
                f"{record.get('excluded_at', '-')}). 검색/생성 대상에서 제외되어 있습니다."
            )
            if st.button("↩ 제외 해제", key=f"unexclude_btn_{document_id}", use_container_width=True):
                registry_path = _registry_path()
                registry = load_identity_registry(str(registry_path))
                if unexclude_document(registry, document_id) is not None and save_identity_registry(registry, str(registry_path)):
                    st.success("제외가 해제되었습니다. 검색되게 하려면 재처리(재색인)가 필요합니다.")
                    st.rerun()
                else:
                    st.error("제외 해제에 실패했습니다.")
        else:
            st.caption("RAW 원본은 삭제되지 않습니다 — 처리 산출물(청크/색인)만 정리하고 향후 처리 대상에서 제외합니다.")
            reason = st.text_input("제외 사유", key=f"exclude_reason_{document_id}")
            confirm = st.checkbox("이 문서를 처리 대상에서 제외하고 기존 색인 데이터를 정리합니다.", key=f"exclude_confirm_{document_id}")
            if st.button("🚫 처리 제외", key=f"exclude_btn_{document_id}", disabled=not confirm, use_container_width=True):
                cleanup = exclude_document_from_index(document_id, output_dir=DEFAULT_OUTPUT_DIR, execute=True)
                registry_path = _registry_path()
                registry = load_identity_registry(str(registry_path))
                if exclude_document(registry, document_id, reason=reason) is not None and save_identity_registry(registry, str(registry_path)):
                    st.success(
                        f"제외 처리되었습니다. TSU 레코드 {cleanup['purged_tsu_records']}건 제거, "
                        f"파일 {len(cleanup['moved_files'])}개를 {cleanup['backup_dir']}/로 이동했습니다."
                    )
                    st.rerun()
                else:
                    st.error("registry 저장에 실패했습니다.")


def _chunks_meta_path(stem: str) -> Path:
    return Path(DEFAULT_OUTPUT_DIR) / f"{stem}_chunks_meta.json"


def _save_chunk_snapshot(stem: str, source_filename: str, document_id: Optional[str], result) -> Path:
    """청킹 미리보기 결과를 {stem}_chunks_meta.json 하나로 병합 저장.

    core.processing.save_chunks()의 죽어있던 포맷(quality 필드까지 포함)을
    그대로 확장한 것 — 새 스키마를 만들지 않고, RAGFlow의 document_id 연결
    개념만 추가하고 청크 본문을 별도 .txt 대신 이 JSON 배열 안에 인라인한다.
    """
    quality = result.quality
    payload = {
        "source": source_filename,
        "document_id": document_id,
        "chunk_count": len(result.chunks),
        "chunk_size": result.params.get("chunk_size"),
        "chunk_overlap": result.params.get("chunk_overlap"),
        "strategy": result.strategy,
        "quality": {
            "avg_noise": quality.avg_noise,
            "max_noise": quality.max_noise,
            "avg_dup": quality.avg_dup,
            "short_ratio": quality.short_ratio,
            "passed": quality.passed,
        },
        "chunks": [
            {"chunk_id": i, "content": chunk}
            for i, chunk in enumerate(result.chunks)
        ],
        "saved_at": datetime.now().isoformat(),
        "saved_from": "library_preview",
    }
    path = _chunks_meta_path(stem)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _render_chunk_preview_section(source_filename: str, doc_type: str) -> None:
    """RAGFlow식 온디맨드 청킹 미리보기 + 명시적 저장.

    처리 완료된 문서의 {stem}.md를 찾아 optimize_chunks()로 그 자리에서 청킹하고
    청크 목록 + 품질 지표(ChunkQuality)를 보여준다. "청킹 실행"만으로는 저장되지
    않고 재실행할 때마다 다시 청킹한다 — 사용자가 "이 결과 저장"을 눌러야만
    {stem}_chunks_meta.json에 병합 저장된다(자동 저장 아님).
    """
    if not source_filename:
        return

    stem = make_safe_stem(source_filename)
    md_matches = list(Path(DEFAULT_OUTPUT_DIR).rglob(f"{stem}.md"))
    if not md_matches:
        return  # 아직 처리되지 않은 문서 — 미리볼 MD가 없음

    with st.expander("🔍 청킹 미리보기", expanded=False):
        state_key = f"_chunk_preview_result_{stem}"

        saved_path = _chunks_meta_path(stem)
        if saved_path.exists():
            try:
                saved_meta = json.loads(saved_path.read_text(encoding="utf-8"))
                st.caption(
                    f"💾 마지막 저장: {saved_meta.get('saved_at', '?')} • "
                    f"청크 {saved_meta.get('chunk_count', '?')}개 • "
                    f"통과 여부: {'✅' if saved_meta.get('quality', {}).get('passed') else '⚠️'}"
                )
            except (json.JSONDecodeError, OSError):
                pass

        if st.button("청킹 실행", key=f"chunk_preview_btn_{stem}"):
            md_text = md_matches[0].read_text(encoding="utf-8")
            st.session_state[state_key] = optimize_chunks(md_text, doc_type.lower())

        result = st.session_state.get(state_key)
        if result is None:
            return

        quality = result.quality
        badge = "✅ 통과" if quality.passed else "⚠️ 기준 미달"
        st.caption(
            f"{badge} • 청크 {len(result.chunks)}개 • 전략={result.strategy} • "
            f"평균 noise={quality.avg_noise:.3f} • 평균 중복={quality.avg_dup:.3f} • "
            f"짧은청크비율={quality.short_ratio:.3f}"
        )

        if st.button("💾 이 결과 저장", key=f"chunk_preview_save_{stem}"):
            document_id, _ = _find_registry_record(source_filename)
            saved = _save_chunk_snapshot(stem, source_filename, document_id, result)
            st.success(f"저장됨: {saved}")

        chunk_lengths = pd.DataFrame(
            {"chunk_idx": list(range(1, len(result.chunks) + 1)),
             "length": [len(c) for c in result.chunks]}
        ).set_index("chunk_idx")
        st.bar_chart(chunk_lengths)

        for i, chunk in enumerate(result.chunks):
            st.text_area(
                f"청크 {i + 1} / {len(result.chunks)} ({len(chunk)}자)",
                chunk,
                height=120,
                key=f"chunk_preview_text_{stem}_{i}",
            )


def _clear_selected_document() -> None:
    """Clear the selected document from StateStore.
    
    Note: This is the direct-clear path (called without rerun). The clear button in the
    detail panel should ideally use on_click=_clear_document_selection for full sync, but
    this function is retained for backward compatibility with any existing direct callers.
    """
    store = StateStore()
    store.delete("library_selected_doc")


def _select_document(doc_path: str, doc_title: str, doc_type: str, doc_size: str, doc_modified: str):
    """Callback for document selection — updates StateStore and triggers full page rerun.
    
    This is the Patch 3 fix (DEFECT-PT-HUMAN-010 Patch 3) that replaces the flawed
    Patch 2 pending-selection approach. Instead of relying on in-cycle session state writes
    (which Streamlit does not re-evaluate after button rendering), we use an explicit
    `on_click` callback that fires AFTER the render cycle, then calls `st.rerun()` to force
    a full page redraw with correct highlight + detail panel synchronization.
    """
    store = StateStore()
    doc = {
        "path": doc_path,
        "title": doc_title,
        "type": doc_type,
        "size": doc_size,
        "modified": doc_modified,
    }
    # Write selection to both StateStore (cross-page persistence) and session state (highlight)
    store.set("library_selected_doc", doc)
    st.session_state["_library_selected_path"] = doc_path
    # Streamlit reruns automatically after an on_click callback returns —
    # calling st.rerun() inside a callback is a no-op and emits a warning.


def _clear_document_selection():
    """Callback for document deselection — clears StateStore and session state."""
    store = StateStore()
    store.delete("library_selected_doc")
    if "_library_selected_path" in st.session_state:
        del st.session_state["_library_selected_path"]
    # on_click callback: Streamlit reruns automatically on return (no st.rerun()).


def _render_document_rows(documents: list[dict]) -> None:
    """Render each document as a selectable row with a selection button.
    
    When the selection button is clicked, the on_click callback (_select_document)
    updates StateStore + session state, then triggers st.rerun() for full-page sync.
    
    Fix (DEFECT-PT-HUMAN-010 Patch 3): Replaced Patch 2's flawed pending-selection approach
    with explicit Streamlit callback mechanism. The `on_click` callback fires after the render
    cycle completes, then st.rerun() forces a full page redraw where all visual elements
    (gray highlight, button state, detail panel) are synchronized on the same pass.
    """
    store = StateStore()

    for i, doc in enumerate(documents):
        # Build a unique key for this document's selection button
        btn_key = f"doc_select_{i}_{hash(doc.get('path', ''))}"
        
        cols = st.columns([5, 1])
        with cols[0]:
            # Compute is_selected from session state _library_selected_path (set by callback)
            selected_path = st.session_state.get("_library_selected_path")
            is_selected = selected_path == doc.get("path")
            card_class = "lib-card selected" if is_selected else "lib-card"
            badge_class = "lib-badge selected" if is_selected else "lib-badge"
            st.markdown(
                f"""
                <div class="{card_class}">
                    <span class="{badge_class}">{doc.get('type', '?')}</span>
                    <div class="lib-title">📄 {doc.get('title', 'Unknown')}</div>
                    <div class="lib-meta">{doc.get('size', '?')} · {doc.get('modified', '?')}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        
        with cols[1]:
            sel_label = "✓ 선택됨" if is_selected else "선택"
            st.button(
                sel_label,
                key=btn_key,
                type="primary" if is_selected else "secondary",
                use_container_width=True,
                on_click=_select_document,
                args=(
                    doc.get("path", ""),
                    doc.get("title", "Unknown"),
                    doc.get("type", "?"),
                    doc.get("size", "?"),
                    doc.get("modified", "?"),
                ),
            )


def _get_documents_list() -> list[dict]:
    """Get the list of source documents from the RAW directory.

    Primary source: DEFAULT_RAW_DIR (raw document queue).
    Supports: .pdf, .epub, .txt, .md, .docx, .html, .htm, .rtf
    Uses recursive search (rglob) to discover all files in subdirectories.
    
    Sort order determined by st.session_state["library_sort_by"]:
    - "name": filename ascending (default)
    - "date": modification time descending (newest first)
    - "size": file size descending (largest first)

    Future extension point: processed output section can be added here
    by iterating DEFAULT_OUTPUT_DIR for already-processed items.
    """
    documents = []
    raw_dir = Path(DEFAULT_RAW_DIR)

    if not raw_dir.exists():
        return documents

    # Supported source document extensions
    SUPPORTED_EXTENSIONS = {".pdf", ".epub", ".txt", ".md", ".docx", ".html", ".htm", ".rtf"}

    # Resolve to absolute for consistent iteration; store display path relative to project root
    raw_resolved = raw_dir.resolve()
    project_root = Path.cwd().resolve()

    for file_path in raw_resolved.rglob("*"):
        # Skip directories and hidden files
        if not file_path.is_file():
            continue
        if file_path.name.startswith("."):
            continue

        # Check extension
        ext = file_path.suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            continue

        try:
            from datetime import datetime
            stat = file_path.stat()
            size_bytes = stat.st_size
            size_kb = size_bytes / 1024
            dt = datetime.fromtimestamp(stat.st_mtime)
            modified_epoch = stat.st_mtime
            modified = dt.strftime("%Y-%m-%d")
        except (AttributeError, OSError):
            size_bytes = 0
            size_kb = "-"
            modified_epoch = 0
            modified = "N/A"

        # Compute display path relative to project root
        try:
            display_path = str(file_path.relative_to(project_root))
        except ValueError:
            display_path = str(file_path)

        documents.append({
            "title": file_path.name,
            "type": ext.lstrip(".").upper(),
            "size": f"{size_kb:.1f} KB" if isinstance(size_kb, (int, float)) else size_kb,
            "modified": str(modified)[:10] if modified != "N/A" else modified,
            "path": display_path,
            "_mtime_epoch": modified_epoch,  # Internal: used for sorting
            "_size_bytes": size_bytes,        # Internal: used for sorting
        })

    # Apply sort order from session state (default: name)
    sort_by = st.session_state.get("library_sort_by", "name")
    
    if sort_by == "date":
        # Modification time descending (newest first)
        documents.sort(key=lambda d: d.get("_mtime_epoch", 0), reverse=True)
    elif sort_by == "size":
        # File size descending (largest first)
        documents.sort(key=lambda d: d.get("_size_bytes", 0), reverse=True)
    else:
        # name ascending (default)
        documents.sort(key=lambda d: d.get("title", ""))

    return documents


def _render_pagination_controls(
    current_page: int,
    total_pages: int,
    total_items: int,
    page_size: int,
) -> None:
    """Render pagination controls with page selector and next/previous buttons.

    Parameters
    ----------
    current_page : int
        Current 1-based page number.
    total_pages : int
        Total number of pages.
    total_items : int
        Total number of filtered items.
    page_size : int
        Number of items per page.
    """
    import streamlit as st

    cols = st.columns([1, 2, 1])

    with cols[0]:
        # Previous button
        if st.button(
            "◀ 이전",
            key="lib_page_prev",
            disabled=current_page <= 1,
            use_container_width=True,
        ):
            st.session_state["library_current_page"] = current_page - 1

    with cols[1]:
        # Page selector dropdown
        page_options = list(range(1, total_pages + 1))
        # For large page counts, show subset around current page
        if total_pages > 7:
            subset = []
            start = max(1, current_page - 3)
            end = min(total_pages, current_page + 3)
            if start > 1:
                subset.append(1)
                if start > 2:
                    subset.append(None)  # ellipsis marker
            subset.extend(range(start, end + 1))
            if end < total_pages:
                if end < total_pages - 1:
                    subset.append(None)
                subset.append(total_pages)
            # Replace None with "..." string for display
            display_options = []
            for opt in subset:
                if opt is None:
                    display_options.append("...")
                else:
                    display_options.append(opt)
            selected = st.selectbox(
                "페이지",
                options=display_options,
                index=display_options.index(current_page),
                key="library_page_selector",
                label_visibility="collapsed",
            )
            # Handle selection
            if isinstance(selected, int) and selected != current_page:
                st.session_state["library_current_page"] = selected
        else:
            selected = st.selectbox(
                "페이지",
                options=page_options,
                index=current_page - 1,
                key="library_page_selector_simple",
                label_visibility="collapsed",
            )
            if selected != current_page:
                st.session_state["library_current_page"] = selected

        # Page info text
        start_item = (current_page - 1) * page_size + 1
        end_item = min(current_page * page_size, total_items)
        st.caption(f"{start_item}–{end_item} / {total_items}")

    with cols[2]:
        # Next button
        if st.button(
            "다음 ▶",
            key="lib_page_next",
            disabled=current_page >= total_pages,
            use_container_width=True,
        ):
            st.session_state["library_current_page"] = current_page + 1


def _format_timestamp(ts) -> str:
    """Format a timestamp to readable date string."""
    from datetime import datetime
    try:
        dt = datetime.fromtimestamp(ts)
        return dt.strftime("%Y-%m-%d %H:%M")
    except (ValueError, OSError):
        return "N/A"
