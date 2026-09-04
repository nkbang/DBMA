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
    # [Root cause fix, SPRINT33-D Preflight 2026-07-23] The size actually
    # used as the "is this a heading?" reference for the size signal —
    # normally equals body_size, but raised to include a second,
    # comparably-sized body text band when one exists (see
    # _effective_size_ceiling). bold_hits/bold candidacy still compares
    # against body_size directly, unaffected by this field.
    size_ceiling: float = 0.0


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


# [Root cause fix, SPRINT33-D Preflight 2026-07-23] Real PDFs — especially
# scanned/OCR'd ones — report the "same" nominal font size with small
# floating-point jitter across spans (e.g. 14.0/14.1/14.2/14.3/14.4 all
# being one 14pt body-text band). Treating each raw float as its own bucket
# fragments a single band into many, and (more importantly, see below)
# masks a second real body-text band from view. Two sizes within this many
# points of each other are treated as the same band.
SIZE_BAND_TOLERANCE = 0.5

# A second size band (above the primary body band) counts as body text —
# not headings — if it has at least this many lines AND at most this
# fraction of them are is_block_top (start of a new block). Real headings
# are structurally block starts (root cause data: "Notes"/"Comment" section
# headings, 86/86 = 100% is_block_top; a genuinely heading-heavy document,
# "8. 사도행전2", 84.3% is_block_top). Wrapped body-text continuation
# lines are not (root cause data: the false-positive ~16.1pt band in "2
# Kings, Anchor Bible Commentary" — quoted Scripture text set larger than
# commentary prose — was only 15.6% is_block_top, 4008 lines).
#
# The line-count requirement has two parts, both needed (2026-07-23
# regression fix): an absolute floor (guards small samples — a handful of
# real headings must not be mistaken for a body band merely because none
# happens to be a block start in a tiny sample) AND a floor relative to the
# primary body band's own line count (guards LARGE documents — a fixed
# absolute floor alone let small noise bands, e.g. 11 and 47 lines out of
# 7705 total in "11. 고린도전서", masquerade as a second body band and
# wrongly suppress that document's real headings down to 0; real secondary
# body bands are comparable in scale to the primary body band, e.g. 4008 of
# ~6353 lines = 63% in the Anchor Bible root-cause case, not a few dozen).
SECONDARY_BAND_MIN_LINES = 30
SECONDARY_BAND_MIN_RELATIVE_SHARE = 0.15
SECONDARY_BAND_MAX_BLOCK_TOP_RATIO = 0.5


def _size_bands(lines: List[_Line]) -> dict:
    """size -> (char_weight, line_count, block_top_count), tolerance-merged
    (see SIZE_BAND_TOLERANCE) so near-duplicate floats (OCR/rendering
    jitter) don't fragment one real font size into many tiny buckets. Band
    keys are the first raw size seen for that band — order-dependent, but
    safe here since real bands in practice are separated by gaps well
    beyond the tolerance (root cause data: ~1.5pt gap between the two real
    bands vs. 0.5pt tolerance), so there is no cross-band merging risk."""
    stats: dict = {}
    for ln in lines:
        band_key = None
        for existing in stats:
            if abs(existing - ln.size) <= SIZE_BAND_TOLERANCE:
                band_key = existing
                break
        if band_key is None:
            band_key = ln.size
        weight, count, block_top = stats.get(band_key, (0, 0, 0))
        stats[band_key] = (
            weight + len(ln.text),
            count + 1,
            block_top + (1 if ln.is_block_top else 0),
        )
    return stats


def _body_size(lines: List[_Line]) -> float:
    bands = _size_bands(lines)
    return max(bands, key=lambda k: bands[k][0]) if bands else 0.0


def _effective_size_ceiling(lines: List[_Line], body: float) -> float:
    """Raises `body` to include any second, comparably-sized body text band
    above it (see SECONDARY_BAND_MIN_LINES/SECONDARY_BAND_MAX_BLOCK_TOP_
    RATIO) — the reference size the "size" signal's SIZE_HEADING_FACTOR
    check should use, so that band isn't swept into heading candidates.
    Returns `body` unchanged when no such secondary band exists (single-
    body-size documents, the common case, are unaffected)."""
    if body <= 0:
        return body
    bands = _size_bands(lines)
    body_stats = bands.get(body)
    if not body_stats:
        return body
    _, body_count, _ = body_stats
    min_required = max(SECONDARY_BAND_MIN_LINES, body_count * SECONDARY_BAND_MIN_RELATIVE_SHARE)
    candidates = [
        size for size, (_, count, block_top) in bands.items()
        if size > body
        and count >= min_required
        and (block_top / count) <= SECONDARY_BAND_MAX_BLOCK_TOP_RATIO
    ]
    return max(candidates) if candidates else body


def profile_document(lines: List[_Line]) -> DocumentProfile:
    """Count plausible size- and bold-signal heading candidates, then select
    the stronger signal.

    A candidate counts only if it passes the OCR letter-ratio filter, so glyph
    noise cannot inflate either signal. Counts are absolute (not fractions) so
    a long document with sparse-but-real headings is not wrongly rejected.
    """
    if not lines:
        return DocumentProfile(0.0, 0, 0, None, 0, 0.0)

    body = _body_size(lines)
    ceiling = _effective_size_ceiling(lines, body)
    short = [ln for ln in lines if len(ln.text) < MAX_HEADING_CHARS]

    size_hits = sum(
        1 for ln in short
        if ln.size > ceiling * SIZE_HEADING_FACTOR and _letter_ratio(ln.text) >= MIN_LETTER_RATIO
    )
    # [Root cause fix, SPRINT33-D Preflight 2026-07-23] is_block_top gates
    # bold candidacy too, mirroring the size-signal fix above — root cause
    # data: "2 Kings, Volume 13" (Hubbard/Barker WBC) had 6768 bold-at-body
    # lines, but only 841 were block starts (real section headers like
    # "Form/Structure/Setting"/"Bibliography" and verse-number markers);
    # the other 5927 were bolded in-body text — overwhelmingly bolded
    # original-language citations (Hebrew words like יהוה, אל, ישראל), not
    # headings. Without this filter, bold_hits was 5100 (vs. 94 for size),
    # so "bold" was selected and every bolded Hebrew word became a false
    # heading candidate.
    bold_hits = sum(
        1 for ln in short
        if ln.bold and ln.size == body and ln.is_block_top and _letter_ratio(ln.text) >= MIN_LETTER_RATIO
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
        size_ceiling=ceiling,
    )


def _signal_strength(line: _Line, profile: DocumentProfile) -> float:
    if profile.selected_signal == "size":
        if profile.size_ceiling <= 0:
            return 0.0
        # 15% larger -> 0.3, 50%+ larger -> 1.0
        return max(0.0, min((line.size / profile.size_ceiling - 1.0) / 0.5, 1.0))
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
        return line.size > profile.size_ceiling * SIZE_HEADING_FACTOR
    if profile.selected_signal == "bold":
        return line.bold and line.size == profile.body_size and line.is_block_top
    return False


def _confidence(line: _Line, profile: DocumentProfile, validity: float) -> float:
    strength = _signal_strength(line, profile)
    bonus = _position_bonus(line)
    return round(max(0.0, min(0.5 * strength + 0.4 * validity + 0.1 * bonus, 1.0)), 4)


def _detect_from_lines(lines: List[_Line]) -> List[HeadingCandidate]:
    """[SPRINT31-D-2] Single authority for heading detection over line-level
    span geometry — pure, no I/O. Both the path-based detect_headings() and
    the span-injection detect_headings_from_spans() funnel through here, so
    they are result-identical by construction."""
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


def _spans_to_lines(spans: List[dict]) -> List[_Line]:
    """Map extractor span records ({text,size,bold,page,is_block_top},
    core.extractors.collect_pdf_spans) to internal _Line objects."""
    return [
        _Line(
            text=s["text"],
            size=s["size"],
            bold=s["bold"],
            page=s["page"],
            is_block_top=s["is_block_top"],
        )
        for s in spans
        if s.get("text")
    ]


def detect_headings_from_spans(spans: List[dict]) -> List[HeadingCandidate]:
    """[SPRINT31-D-2, Option B] Detect headings from pre-collected span
    metadata (core.extractors.collect_pdf_spans) WITHOUT re-opening the PDF —
    the Transitional Adapter removal path (ADR-006 Amendment D). Pure; returns
    [] for empty spans or when no signal is present."""
    return _detect_from_lines(_spans_to_lines(spans))


def detect_headings(path: str, start_page: int = 0, max_pages: Optional[int] = None) -> List[HeadingCandidate]:
    """Detect heading candidates in a PDF by opening it directly. Retained for
    the benchmark and backward compatibility; delegates detection to the same
    core (_detect_from_lines) as detect_headings_from_spans(). Returns [] when
    PyMuPDF is unavailable, no span data exists, or no signal is present.
    Read-only; does not alter extraction, TSU, or any file."""
    lines = _collect_lines(path, start_page=start_page, max_pages=max_pages)
    return _detect_from_lines(lines)
    return out
