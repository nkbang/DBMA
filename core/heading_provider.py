"""
core/heading_provider.py — Heading Provider Registry architecture (SPRINT31-A).

Phase A of the Unified Document Structure Pipeline Initiative. Establishes a
common provider abstraction so every document format (Markdown, PDF, and future
DOCX/HTML/EPUB) can contribute heading structure through one interface, resolved
by source type via a registry — new formats add a provider without touching the
assembler (One Pipeline).

Scope (SPRINT31-A, ADR-006 APPROVED):
  - Provider/Registry/Assembler structure ONLY. This module is dormant: it is
    not yet wired into core/tsu_builder.py, retrieval, or chunking, and it does
    not rebuild any corpus. Wiring is a later phase.
  - PdfHeadingProvider is an explicit Transitional Adapter (ADR-006 Amendment
    D): it re-reads the PDF via core.pdf_structure_detector.detect_headings,
    accepting a temporary "one PDF, two parses" cost until SPRINT31 Phase D
    unifies detection into the extractor span pipeline. It must not become the
    permanent production architecture.
  - HeadingAssembler uses Phase-1 containment matching with an exact whole-line
    guard (no partial "INTRODUCTION"->"INTRO" matches). Offset/page-anchor
    matching is Phase B. Confidence is propagated but not threshold-gated here
    (gating/calibration is Phase C; ADR-006 Amendment A defers physical
    storage to the Calibration phase).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Protocol, runtime_checkable

from core.heading_constants import ATX_HEADING_RE
from core.pdf_structure_detector import detect_headings_from_spans
from core.text_normalizer import normalize_pipeline_text

# Strips a leading ATX marker ("## ") from a line so a chunk line can be
# matched to a provider heading whose text is already marker-free. Bare lines
# (PDF headings, no marker) are unaffected.
_ATX_PREFIX_RE = re.compile(r"^#{1,6}[ \t]+")


# ── Provider output contract ────────────────────────────────────────────────

@dataclass(frozen=True)
class ProviderHeading:
    """One heading contributed by a provider, in document order."""
    text: str
    level: int
    confidence: float
    source: str


@runtime_checkable
class HeadingProvider(Protocol):
    """A provider is constructed bound to a single document and yields that
    document's headings in order."""
    def headings(self) -> List[ProviderHeading]: ...


# ── Concrete providers ──────────────────────────────────────────────────────

class MarkdownProvider:
    """Headings from explicit ATX markers in Markdown/plain text.
    confidence is 1.0 (deterministic)."""

    def __init__(self, text: str) -> None:
        self._text = text or ""

    def headings(self) -> List[ProviderHeading]:
        out: List[ProviderHeading] = []
        for m in ATX_HEADING_RE.finditer(self._text):
            title = m.group(2).strip()
            if title:
                out.append(ProviderHeading(
                    text=title,
                    level=len(m.group(1)),
                    confidence=1.0,
                    source="atx",
                ))
        return out


class PdfHeadingProvider:
    """[SPRINT31-D-3] Headings from PDF span geometry that was already
    collected upstream by the extractor (core.extractors.collect_pdf_spans,
    surfaced as extract_text_from_file(...)['pdf_spans']). Consumes those
    spans via detect_headings_from_spans — it never re-opens the PDF, so the
    "one PDF, two parses" Transitional Adapter (ADR-006 Amendment D) is
    removed and the pipeline reads each PDF once.

    The provider's document is therefore the pre-collected spans, not a file
    path — the provider knows nothing about files, only already-extracted
    data (Unified Extraction Hook)."""

    def __init__(self, spans: List[dict]) -> None:
        self._spans = spans or []

    def headings(self) -> List[ProviderHeading]:
        out: List[ProviderHeading] = []
        for c in detect_headings_from_spans(self._spans):
            out.append(ProviderHeading(
                text=c.text,
                level=1,  # flat for now; size-band -> level is a later phase
                confidence=c.confidence,
                source=f"pdf-{c.signal}",
            ))
        return out


class NullProvider:
    """No-op provider for unknown/unsupported source types — yields no
    headings rather than raising (SPRINT29-C 'honest empty' principle)."""

    def __init__(self, document: object = None) -> None:
        self._document = document

    def headings(self) -> List[ProviderHeading]:
        return []


# ── Registry (resolution only, factory-based) ───────────────────────────────

# A factory takes the document (text or path) and returns a bound provider.
ProviderFactory = Callable[..., HeadingProvider]


class ProviderRegistry:
    """Maps a source type to a provider factory. Resolution only — the
    registry does not itself construct providers (SPRINT31-A decision #2);
    callers apply the resolved factory to their document. Unknown source
    types resolve to NullProvider."""

    def __init__(self) -> None:
        self._factories: Dict[str, ProviderFactory] = {}

    def register(self, source_type: str, factory: ProviderFactory) -> None:
        # Re-registration overwrites — this is the Phase D swap contract
        # (replace the "pdf" adapter with a hook-based provider, assembler
        # untouched).
        self._factories[source_type.lower()] = factory

    def resolve(self, source_type: str) -> ProviderFactory:
        return self._factories.get((source_type or "").lower(), NullProvider)


def _default_registry() -> ProviderRegistry:
    r = ProviderRegistry()
    r.register("md", MarkdownProvider)
    r.register("markdown", MarkdownProvider)
    r.register("txt", MarkdownProvider)  # ATX markers can appear in plain text
    r.register("pdf", PdfHeadingProvider)
    return r


# Module-level singleton (One Execution State).
_REGISTRY = _default_registry()


def get_registry() -> ProviderRegistry:
    return _REGISTRY


# ── Assembler (Phase-1 containment) ─────────────────────────────────────────

@dataclass(frozen=True)
class AssembledHeading:
    heading_path: List[str]
    heading_depth: int
    heading_confidence: float
    heading_source: str


# Headings shorter than this are ignored for matching (guards against
# spurious one/two-char line matches).
_MIN_HEADING_LEN = 2

# [SPRINT31-B-2] Bounded lookahead for cursor recovery: if the next expected
# heading in document order never appears verbatim in the chunk text (OCR
# corruption, an extraction gap, a page-break artifact splitting it across
# lines), a strict single-position cursor stalls forever — every later
# heading, however cleanly it matches, is then silently dropped for the rest
# of the document, since the design only ever compares against the one
# heading it is stuck waiting for. Scanning a small forward window instead
# lets the cursor skip an undetectable heading (it simply never enters
# heading_path — no false match is introduced) and resynchronize on the
# next one that actually appears. Kept small and exact-match-only: this is
# recovery from a missing line, not fuzzy matching.
_LOOKAHEAD_WINDOW = 5


def _normalize_for_matching(text: str) -> str:
    """[SPRINT31-B, Option B3] Put a heading candidate or a chunk line through
    the SAME normalization chunks themselves undergo before splitting
    (core.text_normalizer.normalize_pipeline_text — collapse_soft_linebreaks +
    whitespace/blank-line collapse), after stripping any leading ATX marker.
    This is the "stable coordinate" ADR-006 Phase B settles on: not a raw
    character offset (there is none — postprocess_pdf_text/
    split_front_matter/normalize_pipeline_text all mutate the text before a
    chunk exists, SPRINT31-B Preflight), but a normalized-text space both a
    heading candidate and a chunk line can be projected into and compared
    exactly. A heading matches a chunk only when they are equal in this
    space, so OCR/whitespace noise a candidate and a chunk each separately
    accumulate is neutralized without introducing a substring match (which
    caused the "INTRODUCTION" vs "INTRO" false-positive class the
    Preflight flagged)."""
    stripped = _ATX_PREFIX_RE.sub("", text.strip())
    return normalize_pipeline_text(stripped)


class HeadingAssembler:
    """Assigns a heading path to each chunk by matching provider headings to
    chunk text in normalized-text space (Phase B, Option B3): a heading
    matches a chunk only if its normalized text equals a normalized full line
    of the chunk — so a longer heading is never matched by a shorter
    fragment, and OCR/whitespace variance on either side is absorbed by
    the shared normalization rather than by loosening the match itself.
    Read-only over `chunks` (boundary-preserving). Confidence/source are
    propagated, not gated (Phase C owns thresholds)."""

    def assign(
        self,
        chunks: List[str],
        headings: List[ProviderHeading],
    ) -> List[AssembledHeading]:
        # [SPRINT31-B] Headings are consumed as an ORDERED stream, not a
        # text->heading lookup table. A flat dict keyed by normalized text
        # would collapse duplicate titles (e.g. "Introduction" under both
        # "Chapter 1" and "Chapter 2") to whichever ProviderHeading happened
        # to be inserted last, mis-assigning every earlier occurrence to the
        # wrong chapter. Walking `headings` in document order with a single
        # cursor and only ever comparing against the next unconsumed heading
        # keeps duplicates correctly bound to their own position.
        eligible = [h for h in headings if len(h.text.strip()) >= _MIN_HEADING_LEN]
        normalized_targets = [_normalize_for_matching(h.text) for h in eligible]
        cursor = 0
        # stack of (level, ProviderHeading)
        stack: List[tuple] = []
        results: List[AssembledHeading] = []

        for chunk in chunks:
            for line in (chunk or "").splitlines():
                if not line.strip() or cursor >= len(eligible):
                    continue
                key = _normalize_for_matching(line)
                if not key:
                    continue
                # [SPRINT31-B-2] Look for an exact match within the next
                # window of unconsumed headings, not only at `cursor`. Any
                # headings skipped over (window[0:match_offset]) never
                # appeared verbatim in the text — they are dropped, not
                # guessed at, so no false match is introduced.
                window = normalized_targets[cursor:cursor + _LOOKAHEAD_WINDOW]
                if key not in window:
                    continue
                match_offset = window.index(key)
                h = eligible[cursor + match_offset]
                cursor += match_offset + 1
                while stack and stack[-1][0] >= h.level:
                    stack.pop()
                stack.append((h.level, h))
            if stack:
                top = stack[-1][1]
                results.append(AssembledHeading(
                    heading_path=[ph.text for _, ph in stack],
                    heading_depth=len(stack),
                    heading_confidence=top.confidence,
                    heading_source=top.source,
                ))
            else:
                results.append(AssembledHeading(
                    heading_path=[],
                    heading_depth=0,
                    heading_confidence=0.0,
                    heading_source="",
                ))
        return results
