"""DBMA Design System — Library Workspace Page.

Document library browsing, search, and management interface.
"""

import unicodedata
from typing import Optional

import streamlit as st
from pathlib import Path

from ui.pages._base import BasePage
from ui.theme.colors import THEME
from ui.components.tables import document_table, search_results_table
from ui.state.store import StateStore
from core.config import DEFAULT_RAW_DIR, DEFAULT_OUTPUT_DIR
from core.identity_registry import load_identity_registry, save_identity_registry


def render_library_page() -> None:
    """Render the DBMA Library workspace page."""
    page = BasePage(title="Library", icon="📚")
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
            options=["all", "pdf", "txt", "md", "docx"],
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

    # Add clear selection button — uses on_click callback for full page sync
    st.button(
        "✕ 선택 해제",
        key="clear_selection_btn",
        type="secondary",
        use_container_width=True,
        on_click=_clear_document_selection,
    )


def _registry_path() -> Path:
    return Path(DEFAULT_OUTPUT_DIR) / "registry" / "documents.json"


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
    # Force full page rerun so all visual elements update in sync
    st.rerun()


def _clear_document_selection():
    """Callback for document deselection — clears StateStore and session state."""
    store = StateStore()
    store.delete("library_selected_doc")
    if "_library_selected_path" in st.session_state:
        del st.session_state["_library_selected_path"]
    st.rerun()


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
            label = f"📄 {doc.get('title', 'Unknown')}  •  {doc.get('type', '?')}  •  {doc.get('size', '?')}  •  {doc.get('modified', '?')}"
            if is_selected:
                st.markdown(f'<div style="padding: 6px 12px; background: #e3f2fd; border-radius: 4px; border-left: 3px solid #1976d2;">{label}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div style="padding: 6px 12px;">{label}</div>', unsafe_allow_html=True)
        
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
    Supports: .pdf, .epub, .txt, .md, .docx
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
    SUPPORTED_EXTENSIONS = {".pdf", ".epub", ".txt", ".md", ".docx"}

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
