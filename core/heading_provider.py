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


# Headings shorter than this are ignored for containment matching (guards
# against spurious one/two-char line matches).
_MIN_HEADING_LEN = 2


class HeadingAssembler:
    """Assigns a heading path to each chunk by matching provider headings to
    chunk text. Phase-1 containment with an exact whole-line guard: a heading
    matches a chunk only if the heading text equals a full stripped line of the
    chunk — so a longer heading is never matched by a shorter fragment. Read-
    only over `chunks` (boundary-preserving). Confidence/source are propagated,
    not gated (Phase C owns thresholds)."""

    def assign(
        self,
        chunks: List[str],
        headings: List[ProviderHeading],
    ) -> List[AssembledHeading]:
        by_text = {h.text.strip(): h for h in headings if len(h.text.strip()) >= _MIN_HEADING_LEN}
        # stack of (level, ProviderHeading)
        stack: List[tuple] = []
        results: List[AssembledHeading] = []

        for chunk in chunks:
            for line in (chunk or "").splitlines():
                # Normalize a leading ATX marker so "# Chapter 1" matches the
                # marker-free heading text "Chapter 1"; bare PDF lines are
                # unchanged. The whole-line equality still guards against
                # partial matches (e.g. "INTRODUCT" vs "INTRODUCTION").
                key = _ATX_PREFIX_RE.sub("", line.strip()).strip()
                h = by_text.get(key)
                if h is not None:
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
