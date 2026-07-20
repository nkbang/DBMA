"""
core/semantic_boundary_detector.py — Boundary Score model (SPRINT33-B).

Design phase for the Theological Semantic Chunking Engine roadmap
(SPRINT33-A audit -> SPRINT33-B design/implementation). Establishes a
feature-weighted Boundary Score in place of chunking_optimizer.py's current
pure length threshold, following the exact pattern that made the heading
pipeline (SPRINT31-32) safe to build and validate: a fully dormant module,
unwired, unit-tested in isolation, and later validated against the Beta
corpus before any integration is proposed.

Scope (SPRINT33-B, per HQ Task Order):
  - Signal/event model (BoundaryContext, BoundaryEvent) and a registry
    skeleton (FeatureRegistry) ONLY. This module is not imported by
    core/chunking_optimizer.py, core/tsu_builder.py, or any production path.
  - The first registered feature (HeadingBoundaryFeature) is not a new
    detector: it is core.heading_provider's existing matching primitives
    (_normalize_for_matching, _first_contained) promoted to the
    BoundaryFeatureDetector contract, per HQ's explicit instruction to reuse
    the heading pipeline rather than build a parallel one.
  - [SPRINT33-C Phase 2] ParagraphBoundaryFeature added — deliberately NOT
    a "Blank line" feature too: core.text_normalizer.split_paragraphs()
    splits on blank lines, so every candidate this module ever sees already
    implies one; scoring both would double-count the same signal (SPRINT33-C
    Phase 2 Preflight finding, HQ-approved exclusion).
  - Threshold/weight values here are the SPRINT33-B design draft's initial
    numbers, not calibrated against real corpus data (calibration is a
    later, separately-approved phase, mirroring ADR-006 Amendment B/C for
    the heading pipeline).
  - core/chunking_optimizer.py, core/text_normalizer.py: untouched.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Protocol, runtime_checkable

from core.heading_provider import (
    ProviderHeading,
    _first_contained,
    _normalize_for_matching,
)

# Mirrors HeadingAssembler's own window (core/heading_provider.py) so the
# promoted feature recovers from a missing heading the same way the
# assembler does, rather than introducing a second recovery policy.
_LOOKAHEAD_WINDOW = 5


# ── Signal/event model ──────────────────────────────────────────────────────

@dataclass(frozen=True)
class BoundaryContext:
    """Everything a feature detector needs to score one candidate boundary
    point. `position` is the candidate's ordinal index among all candidates
    generated upstream (e.g. by text_normalizer.split_paragraphs) — this
    module does not generate candidates itself (SPRINT33-A confirmed that
    generation step already exists and needs no reimplementation)."""

    candidate_text: str
    position: int
    headings: List[ProviderHeading] = field(default_factory=list)
    heading_cursor: int = 0
    accumulated_length: int = 0
    chunk_size: int = 0
    min_chunk_size: int = 0


@dataclass(frozen=True)
class BoundaryEvent:
    """One scored boundary candidate — the Detector's output unit. `features`
    holds each feature's weighted contribution (post-multiply), so a caller
    can inspect why a candidate did or didn't cross the threshold."""

    position: int
    features: Dict[str, float]
    total_score: float
    is_boundary: bool


# ── Feature contract (SPRINT33-C anticipatory interface) ───────────────────

@runtime_checkable
class BoundaryFeatureDetector(Protocol):
    """A feature detector scores a single candidate in isolation. Return
    value is a raw, unweighted signal (0.0 = absent, 1.0 = present unless a
    detector documents a different scale) — FeatureRegistry applies the
    configured weight. This keeps a detector ignorant of its own importance,
    so weights can be retuned without touching detector code."""

    def score(self, context: BoundaryContext) -> float: ...


class HeadingBoundaryFeature:
    """[SPRINT33-B] Promotes core.heading_provider's matching primitives to
    a BoundaryFeatureDetector. This is deliberately NOT a call into
    HeadingAssembler.assign() — that method assumes chunks already exist,
    which is exactly the assumption a pre-chunking boundary detector cannot
    make. Instead it reuses the same two primitives HeadingAssembler itself
    is built from (_normalize_for_matching, _first_contained) to ask the
    narrower question those primitives already answer: does this candidate
    text contain one of the next unconsumed headings, word-boundary-guarded.
    Same word-boundary containment rationale as SPRINT32-F applies here
    unchanged."""

    def score(self, context: BoundaryContext) -> float:
        if not context.headings or context.heading_cursor >= len(context.headings):
            return 0.0
        key = _normalize_for_matching(context.candidate_text)
        if not key:
            return 0.0
        window = [
            _normalize_for_matching(h.text)
            for h in context.headings[
                context.heading_cursor : context.heading_cursor + _LOOKAHEAD_WINDOW
            ]
        ]
        return 1.0 if _first_contained(window, key) is not None else 0.0


class ParagraphBoundaryFeature:
    """[SPRINT33-C Phase 2] Scores 1.0 when `candidate_text` is a
    paragraph-level unit — today that is every candidate, since upstream
    candidate generation is core.text_normalizer.split_paragraphs() and
    nothing else feeds this detector. This makes the feature a constant
    contribution under the current one-level candidate generation (a
    deliberate "structural base rate": a paragraph break is boundary-worthy
    by default, and it is negative features — Tiny fragment, Length
    overflow, not yet implemented — that pull specific candidates back
    below threshold, not this feature discriminating among them).

    The definition is written in terms of "is a paragraph unit", not "is
    non-empty", so it stays meaningful rather than becoming dead weight if
    SPRINT33-D introduces a second, finer candidate level (e.g. sentence
    candidates within a paragraph) — at that point this feature starts
    discriminating paragraph-level candidates from sentence-level ones
    without needing to be redefined."""

    def score(self, context: BoundaryContext) -> float:
        return 1.0 if context.candidate_text.strip() else 0.0


# ── Registry (resolution + weighting, mirrors ProviderRegistry's shape) ────

class FeatureRegistry:
    """Maps a feature name to (detector, weight). Registration order does
    not affect scoring (score_all sums all registered features) — this
    mirrors core.heading_provider.ProviderRegistry's resolution-only shape
    so the two registries stay familiar to the same reader."""

    def __init__(self) -> None:
        self._entries: Dict[str, tuple] = {}

    def register(self, name: str, detector: BoundaryFeatureDetector, weight: float) -> None:
        # Re-registration overwrites, same swap contract as ProviderRegistry.
        self._entries[name] = (detector, weight)

    def score_all(self, context: BoundaryContext) -> Dict[str, float]:
        return {
            name: detector.score(context) * weight
            for name, (detector, weight) in self._entries.items()
        }


def _default_registry() -> FeatureRegistry:
    r = FeatureRegistry()
    r.register("heading", HeadingBoundaryFeature(), weight=100.0)
    r.register("paragraph", ParagraphBoundaryFeature(), weight=30.0)
    return r


# Module-level singleton (One Execution State, same pattern as
# core.heading_provider.get_registry).
_REGISTRY = _default_registry()


def get_registry() -> FeatureRegistry:
    return _REGISTRY


# [SPRINT33-B design draft] Initial threshold — uncalibrated. A candidate
# whose weighted feature sum meets or exceeds this is a boundary. Real
# tuning requires Beta-corpus score-distribution analysis, out of scope
# here (see design doc §3/§6).
DEFAULT_THRESHOLD = 50.0


def score_boundary(
    context: BoundaryContext,
    registry: Optional[FeatureRegistry] = None,
) -> BoundaryEvent:
    reg = registry or get_registry()
    features = reg.score_all(context)
    total = sum(features.values())
    return BoundaryEvent(
        position=context.position,
        features=features,
        total_score=total,
        is_boundary=total >= DEFAULT_THRESHOLD,
    )
