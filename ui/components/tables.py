"""DBMA Design System — Table Components.

Professional table displays for document lists and search results.
"""

from typing import Optional

import streamlit as st
from ui.theme.colors import THEME


def document_table(documents: list[dict],
                   columns: Optional[list[str]] = None,
                   searchable: bool = True,
                   filterable: bool = False) -> None:
    """Render a styled document listing table.

    Parameters
    ----------
    documents : list[dict]
        List of document dicts. Each should have at minimum 'title' and 'size'.
    columns : list[str], optional
        Column keys to display. Defaults to ['title', 'type', 'size', 'modified'].
    searchable : bool
        Whether to show a search filter input.
    filterable : bool
        Whether to show type filter dropdown.
    """
    cols_layout = st.columns([3, 20, 5, 8]) if not columns else None

    search_col, *_ = st.columns([1, 19]) if searchable else [None]
    if searchable and search_col:
        query = st.text_input("🔍 문서 검색", placeholder="문서 이름 또는 메타데이터...", key="doc_search_input")
    else:
        query = None

    displayed_docs = documents
    if query:
        query_lower = query.lower()
        displayed_docs = [
            d for d in documents
            if any(query_lower in str(v).lower() for v in d.values())
        ]

    if not displayed_docs:
        st.info("표시할 문서가 없습니다.")
        return

    table_data = []
    for doc in displayed_docs:
        row = [
            _truncate(doc.get("title", "미명"), 50),
            doc.get("type", "document").upper(),
            doc.get("size", "-"),
            doc.get("modified", "-"),
        ]
        table_data.append(row)

    col_headers = columns or ["제목", "형식", "크기", "수정일"]

    df = _import_pandas()
    if df is not None:
        import pandas as pd
        data_df = pd.DataFrame(table_data, columns=col_headers)
        st.dataframe(
            data_df,
            use_container_width=True,
            hide_index=True,
            height=min(len(displayed_docs) * 40 + 38, 400),
        )
    else:
        for row in table_data:
            st.text(" | ".join(str(c) for c in row))


def search_results_table(results: list[dict],
                         score_column: str = "score",
                         highlight_query: Optional[str] = None,
                         clickable_source: bool = False) -> None:
    """Render a styled search results table with relevance scores.

    Parameters
    ----------
    results : list[dict]
        List of result dicts. Each should have 'title', 'score', and metadata.
    score_column : str
        Key for the relevance score field.
    highlight_query : str, optional
        Original search query for highlighting.
    clickable_source : bool
        If True, render source headline as a clickable link
        (uses 'source_file' and 'document_id' from each result dict).
    """
    if not results:
        st.info("검색 결과가 없습니다.")
        return

    if highlight_query:
        st.caption(f"총 {len(results)}개의 결과 (쿼리: \"{highlight_query}\")")

    # Sort by score descending
    sorted_results = sorted(results, key=lambda r: r.get(score_column, 0), reverse=True)

    for i, result in enumerate(sorted_results):
        score = result.get(score_column, 0)
        title = result.get("title", "미제시")
        doc_type = result.get("type", "document").upper()
        snippet = result.get("snippet", "")
        source = result.get("source", "")

        # Score badge color
        if score >= 0.8:
            score_color = THEME.STATUS_SUCCESS
        elif score >= 0.5:
            score_color = THEME.STATUS_WARNING
        else:
            score_color = THEME.STATUS_ERROR

        # Extract source metadata for clickable navigation
        source_file = result.get("source_file", "")
        document_id = result.get("document_id", "")
        can_click = clickable_source and bool(source_file or document_id)

        # Build clickable title if navigation is available
        if can_click:
            nav_key = f"nav_res_{i}_{abs(hash(source_file + str(document_id))) & 0xFFFFFFFF:x}"
            # Use source_file as the display label for the headline
            headline_label = source_file if source_file else title
            html = _render_clickable_result_row(
                i=i,
                title=title,
                score=score,
                doc_type=doc_type,
                snippet=snippet,
                source=source,
                score_color=score_color,
                nav_key=nav_key,
                headline_label=headline_label,
                source_file=source_file,
                document_id=document_id,
            )
        else:
            html = f"""
            <div style="
                background: {THEME.BG_SURFACE};
                border: 1px solid {THEME.BORDER_LIGHT};
                border-radius: 6px;
                padding: {12}px {16}px;
                margin-bottom: {8}px;
            ">
                <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px;">
                    <span style="font-size: 14px; font-weight: 600; color: {THEME.BRAND_PRIMARY};">
                        {i + 1}. {title}
                    </span>
                    <span style="
                        font-size: 12px; font-weight: 700; padding: 2px 8px; border-radius: 4px;
                        background: {score_color}18; color: {score_color};
                    ">
                        RRF {score:.4f}
                    </span>
                </div>
                <div style="font-size: 11px; color: {THEME.TEXT_TERTIARY}; margin-bottom: 4px;">
                    {doc_type}
                    {f' • {source}' if source else ''}
                </div>
                {f'<div style="font-size: 13px; color: {THEME.TEXT_SECONDARY}; line-height: 1.5;">{snippet}</div>' if snippet else ''}
            </div>
            """
        st.markdown(html, unsafe_allow_html=True)


def _render_clickable_result_row(
    i: int,
    title: str,
    score: float,
    doc_type: str,
    snippet: str,
    source: str,
    score_color: str,
    nav_key: str,
    headline_label: str,
    source_file: str,
    document_id: str,
) -> str:
    """Render a search result row with a clickable source headline."""
    # Store navigation target in session state via a hidden widget
    _nav_store_key = f"_dbma_nav_{nav_key}"

    # Hidden button to capture click (Streamlit requires widget for side effects)
    clicked = st.button(
        f"📄 {headline_label}",
        key=nav_key,
        type="primary",
        use_container_width=False,
        help=f"출처: {source_file or 'N/A'}",
    )

    if clicked:
        st.session_state[_nav_store_key] = {
            "source_file": source_file,
            "document_id": document_id,
            "label": headline_label,
            "title": title,
            "score": score,
        }
        st.rerun()

    # Build the HTML row with clickable title span
    title_html = f'<span style="font-size: 14px; font-weight: 600; color: {THEME.BRAND_PRIMARY}; cursor: pointer;">{i + 1}. {headline_label}</span>'

    return f"""
    <div style="
        background: {THEME.BG_SURFACE};
        border: 1px solid {THEME.BORDER_LIGHT};
        border-radius: 6px;
        padding: {12}px {16}px;
        margin-bottom: {8}px;
    ">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px;">
            {title_html}
            <span style="
                font-size: 12px; font-weight: 700; padding: 2px 8px; border-radius: 4px;
                background: {score_color}18; color: {score_color};
            ">
                RRF {score:.4f}
            </span>
        </div>
        <div style="font-size: 11px; color: {THEME.TEXT_TERTIARY}; margin-bottom: 4px;">
            {doc_type}
            {f' • {source}' if source else ''}
        </div>
        {f'<div style="font-size: 13px; color: {THEME.TEXT_SECONDARY}; line-height: 1.5;">{snippet}</div>' if snippet else ''}
    </div>
    """


def _truncate(text: str, max_len: int) -> str:
    """Truncate text to max_len with ellipsis."""
    if len(text) <= max_len:
        return text
    return text[:max_len - 3] + "..."


def _import_pandas():
    """Attempt to import pandas, return None on failure."""
    try:
        import pandas as pd
        return pd
    except ImportError:
        return None