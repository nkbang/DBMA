"""Configuration for the Canonical Normalization Pipeline (Phase 2)."""
from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CORPUS_ROOT = PROJECT_ROOT / "NAE" / "corpus"

RAW_ROOT = CORPUS_ROOT / "raw" / "archive_org"
CANONICAL_ROOT = CORPUS_ROOT / "canonical"

PIPELINE_VERSION = "2.0.0"

# Stage 2.1 - extraction
MIN_OCR_BYTES = 200  # below this, ocr.txt is considered unusable/empty

# Stage 2.2 - structure cleanup
HEADER_FOOTER_MIN_REPEAT = 3     # a line must repeat at least this many times to be a running header/footer
HEADER_FOOTER_MAX_WORDS = 8      # running headers/footers are short
PAGE_NUMBER_PATTERN = r"^\s*(\[?\d{1,4}\]?|[ivxlcdmIVXLCDM]{1,8})\s*$"
FOOTNOTE_MARKER_PATTERN = r"^\s*(\[?\d{1,3}[\.\)]|\*+)\s+\S"
FOOTNOTE_ZONE_LINES = 6          # look for footnote markers in the last N lines of a page
TOC_HEADING_PATTERN = r"^\s*(CONTENTS|TABLE OF CONTENTS|INDEX)\s*$"
TOC_ENTRY_PATTERN = r"^.{2,80}?\.{3,}\s*\d{1,4}\s*$"   # "Chapter One .......... 12"
SCAN_NOISE_PATTERN = r"^[^A-Za-z0-9À-￿]{3,}$"  # lines of only punctuation/symbols

# Stage 2.3 - reflow
VERSE_MAX_CHARS = 45             # short, non-terminal-punctuation lines are treated as verse/poetry
SCRIPTURE_REF_PATTERN = (
    r"\b(?:[1-3]\s?)?[A-Z][a-z]+\.?\s+\d{1,3}:\d{1,3}(?:[-–]\d{1,3})?\b"
)
