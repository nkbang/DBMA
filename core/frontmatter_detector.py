"""
core/frontmatter_detector.py — Front-matter (title/copyright/TOC page)
boundary detection.

Rationale: noise scoring and chunking previously ran over an entire
extracted document as one undifferentiated block. A book's title page,
copyright page, and table of contents are structurally very different
from its body prose (dense short lines, publisher boilerplate, ISBN/
copyright keywords) — scoring/chunking them together with the body either
lets a garbled front matter drag the whole document's noise score up, or
(after averaging across a large body) gets diluted into invisibility.
Neither is a real signal about body content quality.

This module uses the PAGE_BREAK_MARKER that core.extractors inserts
between physical PDF pages to find where front matter ends and body
content begins, using two structural signals per page:
  - front-matter keyword hits (Copyright, ISBN, 판권, 목차, 옮김, ...)
  - short-line density (title pages/TOCs are mostly short lines; prose
    is not)

Front matter is excluded from noise scoring and chunking (core/processing.py)
but is still saved in the .md output for provenance/citation — it is not
discarded, just not treated as searchable body content.
"""

from __future__ import annotations

import re

from core.extractors import PAGE_BREAK_MARKER

_FRONT_MATTER_KEYWORDS = re.compile(
    r"(Copyright|ISBN|All rights reserved|Table of Contents|"
    r"판권|발행처|발행인|\b인쇄\b|옮김|저작권|목차|초판|재판\s*발행)",
    re.IGNORECASE,
)

# Real front matter is virtually never longer than this for the
# single-volume books/commentaries in this corpus. Capping the scan
# bounds how much a false-positive run of short-line-heavy body pages
# (e.g. a chapter opening with a long block quote or list) can accidentally
# get swallowed as "front matter".
MAX_FRONT_MATTER_PAGES = 15

_MIN_BODY_PAGE_CHARS = 400
_MAX_BODY_SHORT_LINE_RATIO = 0.30


def _short_line_ratio(page: str) -> float:
    lines = [ln.strip() for ln in page.splitlines() if ln.strip()]
    if not lines:
        return 0.0
    short = [ln for ln in lines if len(ln) <= 3]
    return len(short) / len(lines)


def _looks_like_front_matter_page(page: str) -> bool:
    stripped = page.strip()
    if not stripped:
        return True  # blank pages interleaved with front matter are common
    if _FRONT_MATTER_KEYWORDS.search(stripped):
        return True
    if len(stripped) < _MIN_BODY_PAGE_CHARS and _short_line_ratio(stripped) > _MAX_BODY_SHORT_LINE_RATIO:
        return True
    return False


def split_front_matter(text: str) -> tuple[str, str]:
    """Split extracted text into (front_matter, body) using page markers.

    Returns ("", text) when there is no page-marker information (e.g.
    non-PDF sources, or extraction paths that don't preserve page
    boundaries yet — see core/extractors.py NEW-5) or when no front
    matter is detected. The two returned strings never contain the raw
    page-break marker — internal page boundaries within each segment are
    normalized back to plain paragraph breaks.
    """
    if not text or PAGE_BREAK_MARKER not in text:
        return "", text or ""

    pages = text.split(PAGE_BREAK_MARKER)

    body_start_page = 0
    for i, page in enumerate(pages[:MAX_FRONT_MATTER_PAGES]):
        if not _looks_like_front_matter_page(page):
            body_start_page = i
            break
    else:
        # Every page scanned looked like front matter — unusual. Be
        # conservative: only ever treat the very first page as front
        # matter in this edge case, rather than risk swallowing real body
        # content into the discarded-from-scoring bucket.
        body_start_page = 1 if len(pages) > 1 else 0

    def _join(parts: list[str]) -> str:
        return "\n\n".join(p.strip() for p in parts if p.strip())

    if body_start_page == 0:
        return "", _join(pages)

    front_matter = _join(pages[:body_start_page])
    body = _join(pages[body_start_page:])
    return front_matter, body
