"""Regression test for extract_from_djvu_xml() (Stage 2.1a page-boundary fix).

Covers the gap found while registering Smith's Bible Dictionary
(Hackett/Abbot American ed.): items with djvu.xml but no hOCR previously
fell straight through to extract_from_ocr(), whose flat _djvu.txt has no
reliable page-break marker and collapses the whole volume into one page.
"""
from __future__ import annotations

from NAE.pipeline.canonical.extract import extract_from_djvu_xml, extract_pages


def _make_djvu_xml_item(tmp_path, *, page_count: int = 3, words_per_line: int = 20):
    item_dir = tmp_path / "raw_item"
    item_dir.mkdir()

    def page_xml(page_num: int) -> str:
        words = " ".join(
            f'<WORD coords="0,0,0,0,0">Word{page_num}_{i}</WORD>' for i in range(words_per_line)
        )
        return (
            f'<OBJECT data="file://p{page_num}.djvu" height="100" '
            f'type="image/x.djvu" usemap="p{page_num}" width="100">'
            f'<PARAM name="PAGE" value="p{page_num}.djvu"/>'
            f"<HIDDENTEXT><PAGECOLUMN></PAGECOLUMN><PAGECOLUMN><REGION>"
            f"<PARAGRAPH><LINE>{words}</LINE></PARAGRAPH>"
            f"</REGION></PAGECOLUMN></HIDDENTEXT></OBJECT>"
        )

    body = "".join(page_xml(i) for i in range(page_count))
    xml = f'<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE DjVuXML>\n<DjVuXML><BODY>{body}</BODY></DjVuXML>'
    (item_dir / "djvu.xml").write_text(xml, encoding="utf-8")
    return item_dir


def test_extract_from_djvu_xml_preserves_page_boundaries(tmp_path):
    item_dir = _make_djvu_xml_item(tmp_path, page_count=5)

    result = extract_from_djvu_xml(item_dir)

    assert result is not None
    assert result.source == "djvu_xml"
    assert len(result.pages) == 5
    assert "Word0_0" in result.pages[0]
    assert "Word4_0" in result.pages[4]
    assert "Word0_0" not in result.pages[4]


def test_extract_from_djvu_xml_missing_file_returns_none(tmp_path):
    item_dir = tmp_path / "raw_item"
    item_dir.mkdir()
    assert extract_from_djvu_xml(item_dir) is None


def test_extract_pages_prefers_djvu_xml_over_flat_ocr_txt(tmp_path):
    item_dir = _make_djvu_xml_item(tmp_path, page_count=4)
    # A flat OCR dump with no form-feed page breaks, as IA's _djvu.txt
    # ships for the Smith's Bible Dictionary volumes — must not win.
    (item_dir / "ocr.txt").write_text("x" * 5000, encoding="utf-8")

    result = extract_pages(item_dir)

    assert result.source == "djvu_xml"
    assert len(result.pages) == 4


def test_extract_pages_hocr_still_wins_over_djvu_xml(tmp_path):
    item_dir = _make_djvu_xml_item(tmp_path, page_count=2)
    words = " ".join(f'<span class="ocrx_word">Hocr{i}</span>' for i in range(20))
    (item_dir / "hocr.html").write_text(
        f'<div class="ocr_page"><p class="ocr_par">'
        f'<span class="ocr_line">{words}</span></p></div>',
        encoding="utf-8",
    )

    result = extract_pages(item_dir)

    assert result.source == "hocr"
