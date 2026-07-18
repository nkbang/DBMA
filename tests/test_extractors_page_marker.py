"""Regression test — core/extractors.py PAGE_BREAK_MARKER preservation
(SPRINT28-B-2).

postprocess_pdf_text() used to destroy \\x0c in two places: _RE_CTRL_F's
control-char sweep deleted it outright, and the subsequent
`.replace('\\x0c', '\\n')` was a dead no-op by the time it ran — either way,
all page boundary information was lost before core/frontmatter_detector.py
ever saw it. This guards both fixed sites.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.extractors import postprocess_pdf_text, PAGE_BREAK_MARKER


def test_pdf_page_marker_preservation():
    text = f"page1 text\n\n{PAGE_BREAK_MARKER}\n\npage2 text"
    out = postprocess_pdf_text(text)
    assert PAGE_BREAK_MARKER in out
    pages = out.split(PAGE_BREAK_MARKER)
    assert len(pages) == 2
    assert "page1 text" in pages[0]
    assert "page2 text" in pages[1]


def test_pdf_page_marker_preserved_across_multiple_pages():
    text = f"\n\n{PAGE_BREAK_MARKER}\n\n".join([f"page {i} content" for i in range(5)])
    out = postprocess_pdf_text(text)
    assert out.count(PAGE_BREAK_MARKER) == 4


def test_other_control_characters_still_stripped():
    # \x01 (SOH) and other control chars must still be removed — only
    # \x0c is exempted from the sweep.
    text = "clean\x01text\x02here"
    out = postprocess_pdf_text(text)
    assert "\x01" not in out
    assert "\x02" not in out
