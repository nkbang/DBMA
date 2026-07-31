"""Stage 2.2 - structural cleanup: headers/footers, page numbers, TOC/index, footnotes, scan noise."""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

from . import config

_PAGE_NUMBER_RE = re.compile(config.PAGE_NUMBER_PATTERN)
_FOOTNOTE_RE = re.compile(config.FOOTNOTE_MARKER_PATTERN)
_TOC_HEADING_RE = re.compile(config.TOC_HEADING_PATTERN, re.IGNORECASE)
_TOC_ENTRY_RE = re.compile(config.TOC_ENTRY_PATTERN)
_SCAN_NOISE_RE = re.compile(config.SCAN_NOISE_PATTERN)


@dataclass
class StructureReport:
    headers_footers_removed: int = 0
    page_numbers_removed: int = 0
    toc_pages_removed: int = 0
    scan_noise_lines_removed: int = 0
    footnotes_extracted: list[dict] = field(default_factory=list)


def _normalize_line_key(line: str) -> str:
    return re.sub(r"\s+", " ", line.strip().lower())


def detect_repeated_lines(pages: list[list[str]]) -> set[str]:
    counter: Counter[str] = Counter()
    for page_lines in pages:
        for line in page_lines:
            key = _normalize_line_key(line)
            if not key or len(key.split()) > config.HEADER_FOOTER_MAX_WORDS:
                continue
            counter[key] += 1
    return {key for key, count in counter.items() if count >= config.HEADER_FOOTER_MIN_REPEAT}


def remove_headers_footers(pages: list[list[str]], repeated: set[str]) -> tuple[list[list[str]], int]:
    removed = 0
    cleaned: list[list[str]] = []
    for page_lines in pages:
        kept = []
        for line in page_lines:
            if _normalize_line_key(line) in repeated:
                removed += 1
                continue
            kept.append(line)
        cleaned.append(kept)
    return cleaned, removed


def remove_page_numbers(pages: list[list[str]]) -> tuple[list[list[str]], int]:
    removed = 0
    cleaned: list[list[str]] = []
    for page_lines in pages:
        kept = []
        for line in page_lines:
            if _PAGE_NUMBER_RE.match(line):
                removed += 1
                continue
            kept.append(line)
        cleaned.append(kept)
    return cleaned, removed


def remove_toc_and_index(pages: list[list[str]]) -> tuple[list[list[str]], int]:
    """Drop whole pages that look like a table of contents / index.

    Guarded by page size: a real TOC/index page is short. Without this guard,
    OCR text lacking form-feed page breaks (see extract.py) is treated as one
    giant "page" spanning the whole book - a single "CONTENTS" line anywhere
    in that text would then match has_heading and delete the entire document.
    """
    removed = 0
    cleaned: list[list[str]] = []
    for page_lines in pages:
        non_blank = [ln for ln in page_lines if ln.strip()]
        if len(non_blank) > config.TOC_MAX_PAGE_LINES:
            cleaned.append(page_lines)
            continue
        has_heading = any(_TOC_HEADING_RE.match(line) for line in page_lines)
        entry_lines = [ln for ln in page_lines if _TOC_ENTRY_RE.match(ln)]
        looks_like_toc = has_heading or (non_blank and len(entry_lines) / max(len(non_blank), 1) > 0.5)
        if looks_like_toc and non_blank:
            removed += 1
            continue
        cleaned.append(page_lines)
    return cleaned, removed


def extract_footnotes(pages: list[list[str]]) -> tuple[list[list[str]], list[dict]]:
    footnotes: list[dict] = []
    cleaned: list[list[str]] = []
    for page_num, page_lines in enumerate(pages, start=1):
        kept = list(page_lines)
        zone_start = max(0, len(kept) - config.FOOTNOTE_ZONE_LINES)
        remaining = []
        for idx, line in enumerate(kept):
            if idx >= zone_start and _FOOTNOTE_RE.match(line):
                footnotes.append({"page": page_num, "text": line.strip()})
                continue
            remaining.append(line)
        cleaned.append(remaining)
    return cleaned, footnotes


def remove_scan_noise(pages: list[list[str]]) -> tuple[list[list[str]], int]:
    removed = 0
    cleaned: list[list[str]] = []
    for page_lines in pages:
        kept = []
        for line in page_lines:
            if line.strip() and _SCAN_NOISE_RE.match(line):
                removed += 1
                continue
            kept.append(line)
        cleaned.append(kept)
    return cleaned, removed


def apply_structure_cleanup(pages: list[list[str]]) -> tuple[list[list[str]], StructureReport]:
    report = StructureReport()

    pages, toc_removed = remove_toc_and_index(pages)
    report.toc_pages_removed = toc_removed

    repeated = detect_repeated_lines(pages)
    pages, hf_removed = remove_headers_footers(pages, repeated)
    report.headers_footers_removed = hf_removed

    pages, pn_removed = remove_page_numbers(pages)
    report.page_numbers_removed = pn_removed

    pages, footnotes = extract_footnotes(pages)
    report.footnotes_extracted = footnotes

    pages, noise_removed = remove_scan_noise(pages)
    report.scan_noise_lines_removed = noise_removed

    return pages, report
