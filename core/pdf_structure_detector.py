"""
core/pdf_structure_detector.py — Adaptive PDF heading detector (SPRINT30-C).

Detection-feasibility only. This module reads PDF span geometry (font size,
bold flag, position) directly via PyMuPDF and produces heading *candidates*
with a confidence score. It is intentionally self-contained:

  - It does NOT touch the flat-text extraction path (core/extractors.py), so
    flat text output is byte-identical to before (SPRINT30-C boundary).
  - It does NOT write to TSU, retrieval, chunking, or production data.
  - Its output is an in-memory benchmark contract, not the TSU
    structure.heading_confidence field (storing that is NOT approved yet).

Design (SPRINT30-B Preflight, grounded in SPRINT30-A measurements):
  1. Per-document signal profiling — measure a size score and a bold score.
  2. Adaptive signal selection — pick whichever signal is stronger; no
     hardcoded per-publisher rule (Korean OCR corpus → size; WBC/Christian
     Focus → bold; measured, not assumed).
  3. OCR validity filter — reject candidates whose letter ratio < 0.6
     (SPRINT30-A: large-font OCR glyph noise like "b냄繼뻐|" otherwise
     pollutes the size signal).
  4. Confidence scoring — 0.5*signal_strength + 0.4*ocr_validity
     + 0.1*position_bonus (Preflight formula; threshold deferred to ADR-006).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Literal, Optional

try:
    import fitz  # PyMuPDF
    _HAS_FITZ = True
except ImportError:  # pragma: no cover - environment guard
    fitz = None  # type: ignore
    _HAS_FITZ = False

# Bold flag bit in PyMuPDF span "flags" (bit 4 == 16).
_BOLD_FLAG = 1 << 4

# A candidate must be at least this fraction real letters (Hangul/Latin) to
# survive the OCR validity filter (SPRINT30-A: 0.6 cleanly separated real
# section titles from large-font glyph noise).
MIN_LETTER_RATIO = 0.6

# Heading lines are short. Longer lines at heading size/weight are body text
# (false-positive risk), excluded from candidacy.
MAX_HEADING_CHARS = 80

# A size must exceed body * this factor to count as a size-signal heading.
SIZE_HEADING_FACTOR = 1.15

# Minimum number of plausible candidates for a signal to be "present" at all.
# Headings are inherently sparse (a handful across dozens of pages), so a
# per-line *fraction* threshold wrongly rejects long documents with real but
# rare headings (SPRINT30-C benchmark finding). An absolute floor is scale-
# invariant: below it the document yields no headings (honest no-op).
MIN_SIGNAL_HITS = 3

_LETTER_RE = re.compile(r"[가-힣A-Za-z]")

Signal = Literal["size", "bold"]


@dataclass(frozen=True)
class HeadingCandidate:
    """Benchmark output contract (NOT a TSU field)."""
    text: str
    page: int
    signal: Signal
    confidence: float
    validity: float


@dataclass
class _Line:
    text: str
    size: float
    bold: bool
    page: int
    is_block_top: bool  # first line of its block (position signal)


@dataclass
class DocumentProfile:
    body_size: float
    size_hits: int          # plausible size-signal heading candidates
    bold_hits: int          # plausible bold-signal heading candidates
    selected_signal: Optional[Signal]
    line_count: int


def _letter_ratio(text: str) -> float:
    t = text.strip()
    if not t:
        return 0.0
    return len(_LETTER_RE.findall(t)) / len(t)


def _collect_lines(path: str, start_page: int = 0, max_pages: Optional[int] = None) -> List[_Line]:
    """Read line-level span geometry from a PDF. Read-only; never modifies the
    document or the flat-text path."""
    if not _HAS_FITZ:
        return []
    try:
        doc = fitz.open(path)
    except Exception:
        # Missing/unreadable/non-PDF file — degrade to no headings rather than
        # raise (detector is a read-only best-effort probe).
        return []
    n = len(doc)
    end = n if max_pages is None else min(n, start_page + max_pages)
    lines: List[_Line] = []
    for pno in range(start_page, end):
        for block in doc[pno].get_text("dict").get("blocks", []):
            block_lines = block.get("lines", [])
            for li, line in enumerate(block_lines):
                spans = line.get("spans", [])
                if not spans:
                    continue
                dom = max(spans, key=lambda s: len(s["text"]))
                text = "".join(s["text"] for s in spans).strip()
                if not text:
                    continue
                lines.append(_Line(
                    text=text,
                    size=round(dom["size"], 1),
                    bold=bool(dom["flags"] & _BOLD_FLAG),
                    page=pno,
                    is_block_top=(li == 0),
                ))
    doc.close()
    return lines


def _body_size(lines: List[_Line]) -> float:
    weight: dict = {}
    for ln in lines:
        weight[ln.size] = weight.get(ln.size, 0) + len(ln.text)
    return max(weight, key=lambda k: weight[k]) if weight else 0.0


def profile_document(lines: List[_Line]) -> DocumentProfile:
    """Count plausible size- and bold-signal heading candidates, then select
    the stronger signal.

    A candidate counts only if it passes the OCR letter-ratio filter, so glyph
    noise cannot inflate either signal. Counts are absolute (not fractions) so
    a long document with sparse-but-real headings is not wrongly rejected.
    """
    if not lines:
        return DocumentProfile(0.0, 0, 0, None, 0)

    body = _body_size(lines)
    short = [ln for ln in lines if len(ln.text) < MAX_HEADING_CHARS]

    size_hits = sum(
        1 for ln in short
        if ln.size > body * SIZE_HEADING_FACTOR and _letter_ratio(ln.text) >= MIN_LETTER_RATIO
    )
    bold_hits = sum(
        1 for ln in short
        if ln.bold and ln.size == body and _letter_ratio(ln.text) >= MIN_LETTER_RATIO
    )

    selected: Optional[Signal]
    if max(size_hits, bold_hits) < MIN_SIGNAL_HITS:
        selected = None
    elif bold_hits >= size_hits:
        selected = "bold"
    else:
        selected = "size"

    return DocumentProfile(
        body_size=body,
        size_hits=size_hits,
        bold_hits=bold_hits,
        selected_signal=selected,
        line_count=len(lines),
    )


def _signal_strength(line: _Line, profile: DocumentProfile) -> float:
    if profile.selected_signal == "size":
        if profile.body_size <= 0:
            return 0.0
        # 15% larger -> 0.3, 50%+ larger -> 1.0
        return max(0.0, min((line.size / profile.body_size - 1.0) / 0.5, 1.0))
    # bold signal is reliable-but-binary per line
    return 0.8 if line.bold else 0.0


def _position_bonus(line: _Line) -> float:
    if len(line.text) < 40 and line.is_block_top:
        return 0.2
    if len(line.text) < 40 or line.is_block_top:
        return 0.1
    return 0.0


def _is_candidate(line: _Line, profile: DocumentProfile) -> bool:
    if len(line.text) >= MAX_HEADING_CHARS:
        return False
    if _letter_ratio(line.text) < MIN_LETTER_RATIO:
        return False
    if profile.selected_signal == "size":
        return line.size > profile.body_size * SIZE_HEADING_FACTOR
    if profile.selected_signal == "bold":
        return line.bold and line.size == profile.body_size
    return False


def _confidence(line: _Line, profile: DocumentProfile, validity: float) -> float:
    strength = _signal_strength(line, profile)
    bonus = _position_bonus(line)
    return round(max(0.0, min(0.5 * strength + 0.4 * validity + 0.1 * bonus, 1.0)), 4)


def detect_headings(path: str, start_page: int = 0, max_pages: Optional[int] = None) -> List[HeadingCandidate]:
    """Detect heading candidates in a PDF. Returns [] when PyMuPDF is
    unavailable, no span data exists, or no signal is present (honest no-op).
    Read-only; does not alter extraction, TSU, or any file."""
    lines = _collect_lines(path, start_page=start_page, max_pages=max_pages)
    profile = profile_document(lines)
    if profile.selected_signal is None:
        return []
    out: List[HeadingCandidate] = []
    for ln in lines:
        if not _is_candidate(ln, profile):
            continue
        validity = _letter_ratio(ln.text)
        out.append(HeadingCandidate(
            text=ln.text,
            page=ln.page,
            signal=profile.selected_signal,
            confidence=_confidence(ln, profile, validity),
            validity=round(validity, 4),
        ))
    return out
