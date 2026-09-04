"""NAE Citation / Provenance Card Component.

Rendered as a styled card with:
- Author (저자)
- Source (출처)
- Text location (본문 위치)
- Document type (자료 유형)
- Relevance stars (관련성 별점)
- Two action buttons (원문 다시 보기 / 인용하기)

Fields without data are omitted entirely — no "N/A" placeholders.
Buttons use real st.button() with callbacks — never dead HTML elements.
Based on DBMA-UX-007 §6 specification.
"""

import streamlit as st

from ui.theme.colors import DBMADesignSystemColors as THEME


def _stars_html(score: float, color: str) -> str:
    """Return ★/☆ HTML string for a 0..1 score."""
    filled = min(5, max(0, round(score * 5)))
    empty = 5 - filled
    return (f'<span style="color:{color}">&#9733;</span>' * filled +
            f'<span style="color:{THEME.CITE_STAR_EMPTY}">&#9734;</span>' * empty)


def render_citation_card(
    *,
    source_file: str,
    text_location: str | None = None,
    doc_type: str | None = None,
    author: str | None = None,
    citation_title: str | None = None,
    relevance_score: float = 0.0,
    on_view_original: bool = False,
    on_copy_citation: bool = False,
    key_suffix: str = "",
) -> None:
    """Render a citation/provenance card per DBMA-UX-007 §6.

    Parameters
    ----------
    source_file : str
        Source document filename (e.g. "9. 로마서1.pdf").
    text_location : str, optional
        Text location (e.g. "로마서 8:1-4"). Omitted if None/empty.
    doc_type : str, optional
        Document type label (e.g. "성경 주석"). Omitted if None/empty.
    author : str, optional
        Source author name. Omitted if None/empty.
    citation_title : str, optional
        Source title / publication name. Omitted if None/empty.
    relevance_score : float
        Relevance score 0..1 — rendered as ★★★☆☆ style.
    on_view_original : bool
        If True, render "원문 다시 보기" button (real st.button).
    on_copy_citation : bool
        If True, render "인용하기" button (real st.button).
    """
    # Build meta rows — only include fields with data
    meta_rows: list[str] = []

    if author:
        meta_rows.append(f"<dt>저자</dt><dd>{author}</dd>")
    if citation_title:
        meta_rows.append(f"<dt>출처</dt><dd>{citation_title}</dd>")
    if source_file:
        meta_rows.append(f"<dt>문서</dt><dd>{source_file}</dd>")
    if text_location:
        meta_rows.append(f"<dt>본문 위치</dt><dd>{text_location}</dd>")
    if doc_type:
        meta_rows.append(f"<dt>자료 유형</dt><dd>{doc_type}</dd>")

    meta_html = "".join(meta_rows) if meta_rows else ""

    stars = _stars_html(relevance_score, THEME.CITE_STAR_FILLED)

    # Render card container with real st.button() below it
    card_html = f"""
    <div style="
        background:{THEME.CITE_BG};
        border:1px solid {THEME.CITE_BORDER};
        border-left:4px solid {THEME.CITE_STAR_FILLED};
        border-radius:8px;
        padding:16px 20px;
        margin-top:8px;
    ">
        <dl style="display:grid;grid-template-columns:auto 1fr;gap:4px 12px;
                    font-size:13px;margin-bottom:8px;">
            {meta_html}
        </dl>
        <div style="font-size:13px;color:{THEME.TEXT_SECONDARY};">
            {stars} 관련성 — 검색어와의 연관성 기준
        </div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)

    # Real Streamlit buttons (not HTML) — placed below the card
    btn_key_base = f"cite_btn_{abs(hash(source_file + key_suffix)) & 0xFFFFFFFF:x}"
    if on_view_original:
        st.button(
            "원문 다시 보기",
            key=f"{btn_key_base}_view",
            use_container_width=True,
        )
    if on_copy_citation:
        st.button(
            "인용하기",
            key=f"{btn_key_base}_copy",
            use_container_width=True,
        )


