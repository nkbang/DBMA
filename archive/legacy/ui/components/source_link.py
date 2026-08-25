"""DBMA Source Link Component — unified source document navigation.

Provides clickable source links that navigate to DBMA Library document detail
view instead of external URLs.

Usage:
    from ui.components.source_link import source_link

    # In chat or research UI:
    source_link(candidate)  # renders clickable source headline
"""

from typing import Any, Optional

import streamlit as st


def _get_library_page():
    """Lazy import to avoid circular dependencies."""
    from streamlit.navigation.page import StreamlitPage
    from ui.pages.library import render_library_page
    # Return the library page object for navigation
    return render_library_page


def source_link(
    candidate: Any,
    label: Optional[str] = None,
    expanded: bool = False,
) -> None:
    """Render a clickable source link that navigates to Library detail.

    Parameters
    ----------
    candidate : RankedCandidate | dict
        A retrieval result with metadata including source_file and document_id.
    label : str, optional
        Custom display label. If None, uses heading_path or source_file.
    expanded : bool
        Whether the source block is initially expanded (for chat expander context).

    Navigation flow:
        Source headline → source_file → Library detail panel
    """
    # Extract metadata safely (supports both dataclass and dict)
    metadata = getattr(candidate, "metadata", candidate) if candidate else {}
    if not isinstance(metadata, dict):
        metadata = {}

    source_file = metadata.get("source_file", "")
    document_id = metadata.get("document_id", "")
    heading_path = metadata.get("structure", {}).get("heading_path", [])

    # Build display label
    if label:
        display_label = label
    elif heading_path:
        display_label = " > ".join(heading_path)
    elif source_file:
        display_label = source_file
    else:
        display_label = "출처 미상"

    # Check navigation feasibility
    can_navigate = bool(source_file or document_id)

    if can_navigate:
        # Build a unique key for this link
        link_key = f"source_link_{id(candidate)}_{hash(source_file + str(document_id))}"

        # Render clickable link
        if st.button(
            f"📄 {display_label}",
            key=link_key,
            type="primary" if can_navigate else "secondary",
            use_container_width=True,
            disabled=not can_navigate,
        ):
            # Store source info for Library to pick up
            _store_source_selection(source_file, document_id, display_label)
            # Trigger page rerun to show Library detail
            st.rerun()

        # Show score and metadata
        score = getattr(candidate, "final_score", 0.0)
        st.caption(f"신뢰도: {score:.4f} · {source_file or '출처 미상'}")
    else:
        # Graceful degradation: show non-clickable text
        st.caption(f"출처 정보 부족: {display_label}")


def _store_source_selection(
    source_file: str,
    document_id: str,
    display_label: str,
) -> None:
    """Store source selection in session state for Library detail panel."""
    st.session_state["_dbma_source_nav"] = {
        "source_file": source_file,
        "document_id": document_id,
        "label": display_label,
    }


def get_pending_source_nav() -> Optional[dict]:
    """Retrieve and clear pending source navigation request."""
    nav = st.session_state.pop("_dbma_source_nav", None)
    return nav


def render_pending_source_detail() -> None:
    """Render the pending source detail in Library-style format.

    Call this from a page that wants to display source document details.
    Shows the document info if there's a pending navigation request.
    """
    nav = get_pending_source_nav()
    if not nav:
        return

    source_file = nav.get("source_file", "")
    label = nav.get("label", "출처")

    st.divider()
    st.subheader(f"📄 출처 문서: {label}")

    # Show available metadata
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"**파일:** {source_file or 'N/A'}")
    with c2:
        st.markdown(f"**출처 헤드라인:** {label}")
        st.caption("Library에서 전체 문서 상세를 확인하세요.")

    # Clear button
    if st.button("닫기", type="secondary"):
        st.rerun()