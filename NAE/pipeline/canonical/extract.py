"""Stage 2.1a - extract raw per-page text from OCR TXT (preferred) or PDF (fallback)."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from . import config

logger = logging.getLogger("nae.canonical.extract")


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
    """OCR TXT is preferred; PDF text extraction is the fallback."""
    result = extract_from_ocr(item_dir)
    if result is not None:
        return result
    result = extract_from_pdf(item_dir)
    if result is not None:
        return result
    return ExtractionResult(pages=[], source="none")
