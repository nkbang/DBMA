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
                         highlight_query: Optional[str] = None) -> None:
    """Render a styled search results table with relevance scores.

    Parameters
    ----------
    results : list[dict]
        List of result dicts. Each should have 'title', 'score', and metadata.
    score_column : str
        Key for the relevance score field.
    highlight_query : str, optional
        Original search query for highlighting.
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

        # [DBMA-UX-007 §11] RRF 알고리즘명 + 원시 소수점은 금지 — 별점으로 단순화
        filled = min(5, max(0, round(score * 5)))
        stars = "\u2b50" * filled + "\u2606" * (5 - filled)

        html = f"""
        <div style="
            background: {THEME.BG_SURFACE};
            border: 1px solid {THEME.BORDER_LIGHT};
            border-radius: 8px;
            padding: {14}px {18}px;
            margin-bottom: {10}px;
        ">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px;">
                <span style="font-size: 14px; font-weight: 600; color: {THEME.BRAND_PRIMARY};">
                    {i + 1}. {title}
                </span>
                <span style="
                    font-size: 12px; font-weight: 700; padding: 2px 8px; border-radius: 4px;
                    background: {score_color}18; color: {score_color};
                ">
                    {stars}
                </span>
            </div>
            <div style="font-size: 11px; color: {THEME.TEXT_TERTIARY}; margin-bottom: 6px;">
                {doc_type}
                {f' • {source}' if source else ''}
            </div>
            {f'<div style="font-family: Source Serif 4, serif; font-style: italic; font-size: 13px; color: {THEME.TEXT_SECONDARY}; line-height: 1.6;">{snippet}</div>' if snippet else ''}
        </div>
        """
        st.markdown(html, unsafe_allow_html=True)


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