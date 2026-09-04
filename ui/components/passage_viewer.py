"""ui/components/passage_viewer.py — 성경 본문 선택 뷰어 (ADR-031).

책 → 장 → 절 범위를 고르면 해당 절 본문을 보여주고,
`core.retrieval.ScriptureReference` 를 돌려준다. 본문 텍스트는 사용자가
등록한 성경 JSON(`core.bible_text.load_bible_text`)에서 온다.
"""

from __future__ import annotations

from typing import Optional

import streamlit as st

from core.bible_text import BibleText
from core.retrieval import ScriptureReference


def render_passage_viewer(
    bible: BibleText, *, key_prefix: str = "passage_viewer"
) -> Optional[ScriptureReference]:
    """성경뷰어를 렌더하고 현재 선택된 본문 참조를 반환한다.

    성경 JSON 이 없거나(사용자가 아직 등록 안 함) 선택 범위에 본문이 없으면
    안내만 표시하고 None 을 반환한다.
    """
    if not bible.available:
        st.info(bible.reason)
        return None

    books = bible.list_books()
    if not books:
        st.info("등록된 성경 책이 없습니다. 성경 JSON 의 'books' 항목을 확인하세요.")
        return None

    st.caption(f"성경 본문: {bible.version_label}")

    name_by_id = {bid: name for bid, name in books}
    book_id = st.selectbox(
        "책",
        options=[bid for bid, _ in books],
        format_func=lambda bid: name_by_id.get(bid, bid),
        key=f"{key_prefix}_book",
    )

    n_chapters = max(1, bible.chapter_count(book_id))
    chapter = int(
        st.number_input(
            "장",
            min_value=1,
            max_value=n_chapters,
            value=1,
            step=1,
            key=f"{key_prefix}_chapter",
        )
    )

    n_verses = max(1, bible.verse_count(book_id, chapter))
    col_start, col_end = st.columns(2)
    with col_start:
        verse_start = int(
            st.number_input(
                "절 (시작)",
                min_value=1,
                max_value=n_verses,
                value=1,
                step=1,
                key=f"{key_prefix}_vstart",
            )
        )
    with col_end:
        verse_end = int(
            st.number_input(
                "절 (끝)",
                min_value=verse_start,
                max_value=max(verse_start, n_verses),
                value=verse_start,
                step=1,
                key=f"{key_prefix}_vend",
            )
        )

    verses = bible.get_verses(book_id, chapter, verse_start, verse_end)
    if not verses:
        st.caption("해당 범위의 절 본문을 찾지 못했습니다.")
        return None

    with st.container(border=True):
        for num, text in verses:
            st.markdown(f"**{num}** {text}")

    return ScriptureReference(
        book_id=book_id,
        chapter=chapter,
        verse_start=verse_start,
        verse_end=verse_end if verse_end != verse_start else None,
    )
