"""Stage 2.1a - extract raw per-page text from hOCR (preferred), OCR TXT, or PDF (fallback)."""
from __future__ import annotations

import html
import logging
import re
from dataclasses import dataclass
from pathlib import Path

from . import config

logger = logging.getLogger("nae.canonical.extract")

_HOCR_PAGE_SPLIT_RE = re.compile(r'<div class="ocr_page"')
_HOCR_PAR_SPLIT_RE = re.compile(r'<p class="ocr_par"')
_HOCR_LINE_SPLIT_RE = re.compile(r'<span class="ocr_line"')
_HOCR_WORD_RE = re.compile(r'<span class="ocrx_word"[^>]*>([^<]*)</span>')


@dataclass
class ExtractionResult:
    pages: list[str]
    source: str  # "ocr" | "pdf" | "none"


def _split_ocr_pages(text: str) -> list[str]:
    if "\x0c" in text:
        return text.split("\x0c")
    return [text]


def _looks_like_text(text: str, *, sample_size: int = 4000) -> bool:
    """Reject binary/compressed content that slipped past file-selection (e.g. gzip, HOCR markup).

    The UTF-8 replacement character (U+FFFD) is technically "printable" but only
    ever appears from decoding invalid byte sequences, so it is treated as garbage
    alongside control characters rather than counted as valid text.
    """
    sample = text[:sample_size]
    if not sample.strip():
        return False
    garbage = sum(1 for ch in sample if ch == "�" or (not ch.isprintable() and ch not in "\n\r\t"))
    return (garbage / len(sample)) < 0.05


def extract_from_hocr(item_dir: Path) -> ExtractionResult | None:
    """hOCR HTML, preferred over plain OCR text when both exist.

    hOCR carries explicit ocr_page/ocr_line boundaries, which Stage 2.2
    (structure.py) depends on for header/footer repetition detection,
    page-number stripping, and TOC/index page removal. Plain OCR text
    (e.g. Internet Archive's DjVu-derived _djvu.txt) is not guaranteed to
    include form-feed (\\x0c) page breaks — when it doesn't, the whole
    document collapses into a single "page" and those per-page heuristics
    never fire at all (confirmed on PBC1765: djvu.txt had 0 form-feeds,
    page_count came out as 1, and 65% of the first 60 extracted paragraphs
    were unremoved scan noise as a result).

    Per-word x_wconf confidence is present in hOCR but is NOT used to filter
    words here — checked directly against PBC1765's hOCR: confidence was
    uniformly low (median 2/100) across both genuine body text and obvious
    noise, so it does not discriminate signal from noise for this kind of
    period typography (long-s, blackletter-adjacent serifs) and would risk
    stripping real content along with noise. Only the page/line/paragraph
    structure is used, not confidence-based word filtering.

    Blank lines are inserted between hOCR ocr_par blocks (not just between
    lines within a paragraph) because reflow.py's _split_blocks() uses a
    blank line as its sole paragraph-boundary signal — without this, an
    entire page's ocr_lines run together into one giant "paragraph" and
    both paragraph splitting and heading detection (which operates on
    individual paragraphs) collapse to near-nothing (confirmed: an earlier
    version of this function that only preserved line breaks, not
    paragraph breaks, produced paragraph_count=2 for the whole ~127k
    character document).
    """
    hocr_path = item_dir / "hocr.html"
    if not hocr_path.exists() or hocr_path.stat().st_size < config.MIN_OCR_BYTES:
        return None
    raw_html = hocr_path.read_text(encoding="utf-8", errors="replace")
    if "ocr_page" not in raw_html:
        return None

    pages: list[str] = []
    for page_chunk in _HOCR_PAGE_SPLIT_RE.split(raw_html)[1:]:
        paragraphs: list[str] = []
        for par_chunk in _HOCR_PAR_SPLIT_RE.split(page_chunk)[1:]:
            lines: list[str] = []
            for line_chunk in _HOCR_LINE_SPLIT_RE.split(par_chunk)[1:]:
                words = [html.unescape(w).strip() for w in _HOCR_WORD_RE.findall(line_chunk)]
                line_text = " ".join(w for w in words if w)
                if line_text:
                    lines.append(line_text)
            if lines:
                paragraphs.append("\n".join(lines))
        pages.append("\n\n".join(paragraphs))
    if not pages:
        return None
    return ExtractionResult(pages=pages, source="hocr")


def extract_from_ocr(item_dir: Path) -> ExtractionResult | None:
    ocr_path = item_dir / "ocr.txt"
    if not ocr_path.exists() or ocr_path.stat().st_size < config.MIN_OCR_BYTES:
        return None
    text = ocr_path.read_text(encoding="utf-8", errors="replace")
    if not _looks_like_text(text):
        logger.warning("[extract] %s does not look like plain text, falling back", ocr_path)
        return None
    return ExtractionResult(pages=_split_ocr_pages(text), source="ocr")


def extract_from_pdf(item_dir: Path) -> ExtractionResult | None:
    pdf_candidates = list(item_dir.glob("original.pdf"))
    if not pdf_candidates:
        return None
    try:
        import fitz  # PyMuPDF
    except ImportError:
        logger.error("[extract] PyMuPDF not installed, cannot extract %s", pdf_candidates[0])
        return None

    pages: list[str] = []
    with fitz.open(pdf_candidates[0]) as doc:
        for page in doc:
            pages.append(page.get_text("text"))
    if not pages:
        return None
    return ExtractionResult(pages=pages, source="pdf")


def extract_pages(item_dir: Path) -> ExtractionResult:
    """hOCR (page-structure-aware) is preferred; plain OCR TXT next; PDF
    text extraction is the last-resort fallback."""
    result = extract_from_hocr(item_dir)
    if result is not None:
        return result
    result = extract_from_ocr(item_dir)
    if result is not None:
        return result
    result = extract_from_pdf(item_dir)
    if result is not None:
        return result
    return ExtractionResult(pages=[], source="none")
