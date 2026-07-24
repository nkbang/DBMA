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
  - [SPRINT33-C Phase 4-A] TinyFragmentPenaltyFeature added — negative
    weight, reuses core.config.DEFAULT_MIN_CHUNK_SIZE (SSOT, SPRINT29-B)
    rather than a re-hardcoded threshold. First feature to use
    BoundaryContext.min_chunk_size, reserved since SPRINT33-B for exactly
    this.
  - [SPRINT33-C Phase 4-B] SentenceBoundaryConfidenceFeature added — reuses
    core.text_normalizer._ends_like_sentence (SPRINT33-C Phase 4-B
    Preflight: already the exact primitive collapse_soft_linebreaks itself
    uses per-line to decide short-line merges, applied here to a
    candidate's last non-empty line). Named for what it measures today
    (confidence that the candidate ends at a real sentence boundary, not a
    truncation) rather than "Completion", so a later Phase 5 pivot to a
    negative "cut mid-sentence" penalty needs no rename.
  - [SPRINT33-C Phase 4-C] ScriptureReferenceBoundaryFeature added — reuses
    core.retrieval.QueryParser (the exact class core/tsu_builder.py's
    _reference_parser already is, for verse_mapping resolution), but only
    scores a reference found within the candidate's first
    core.config.SCRIPTURE_REFERENCE_HEAD_WINDOW characters as a boundary
    signal. Phase 4-C's overlap Preflight measured that scoring ANY
    reference anywhere in a candidate would fire on incidental in-body
    citations for ~78.5% of the ref-bearing, heading-unmatched sample —
    restricting to the head window keeps this a heading-shaped signal
    (title + reference at the start) instead of a body-content detector.
  - Threshold/weight values here are the SPRINT33-B design draft's initial
    numbers, not calibrated against real corpus data (calibration is a
    later, separately-approved phase, mirroring ADR-006 Amendment B/C for
    the heading pipeline).
  - core/chunking_optimizer.py, core/text_normalizer.py: untouched.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Protocol, runtime_checkable

from core.config import (
    DEFAULT_MIN_CHUNK_SIZE,
    EMBEDDING_SIMILARITY_DROP_THRESHOLD,
    EMBEDDING_SIMILARITY_WEIGHT,
    PAGE_HEADER_ARTIFACT_WEIGHT,
    SCRIPTURE_REFERENCE_HEAD_WINDOW,
    SCRIPTURE_REFERENCE_WEIGHT,
)
from core.embedder import get_embedder as _get_embedder
from core.heading_provider import (
    ProviderHeading,
    _first_contained,
    _normalize_for_matching,
)
from core.repetition_detector import RepetitionSignal
from core.retrieval import QueryParser
from core.text_normalizer import _ends_like_sentence

# [ADR-008 제안 3 수정, 2026-07-21] core.embedder.embed()는 문서에는
# "폴백"으로 적혀 있지만 실제로는 legacy MiniLM(768차원)만 로드하는
# 함수다 — core.config.EMBEDDING_DIMENSION(1024, bge-m3 기준)과 맞지
# 않아 항상 DimensionMismatchError를 던진다. 실측(Axis 2 재측정)에서
# 이 예외가 EmbeddingSimilarityBoundaryFeature의 안전 폴백(except
# Exception: return 0.0)에 조용히 삼켜져, feature가 "유사도가 높아
# 안 켜짐"이 아니라 "매 호출이 실패해 전혀 작동하지 않음" 상태였음이
# 드러났다. core.retrieval.py가 실제로 쓰는 진입점인
# get_embedder()(Ollama bge-m3 우선, 실패 시 MiniLM 폴백)로 교체.
_embedder = _get_embedder()


def _cosine_similarity(a, b) -> float:
    import numpy as np

    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))

# Same QueryParser instance role as core.tsu_builder._reference_parser —
# a stateless parser, safe to share across scoring calls.
_reference_parser = QueryParser()

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
    # [ADR-008 제안 3] EmbeddingSimilarityBoundaryFeature 전용 — 현재
    # 버퍼의 마지막 후보 텍스트(hierarchical_chunk_builder.build_chunks()
    # 의 buf[-1]). 버퍼가 비어 있으면(문서/청크 시작 직후) 빈 문자열 —
    # 이 경우 feature는 신호 없음(0.0)으로 안전하게 폴백한다.
    previous_candidate_text: str = ""
    # [ADR-011 제안 3] PageHeaderArtifactFeature 전용 — 호출자(문서 단위로
    # 생성된 core.repetition_detector.RepetitionTracker)가 이 candidate에
    # 대해 이미 observe()를 호출해 얻은 신호. None이면(기존 호출부) 이
    # feature는 신호 없음(0.0)으로 안전하게 폴백한다 — 다른 feature와
    # 동일한 계약.
    repetition_signal: Optional[RepetitionSignal] = None


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


class TinyFragmentPenaltyFeature:
    """[SPRINT33-C Phase 4] Fires (1.0, meant to be paired with a negative
    weight) when a candidate is shorter than the SSOT minimum chunk size
    (core.config.DEFAULT_MIN_CHUNK_SIZE, SPRINT29-B single-source-of-truth
    — not re-hardcoded here). `context.min_chunk_size` overrides it when a
    caller sets one, same pattern chunk_size/accumulated_length were
    reserved for in BoundaryContext since SPRINT33-B.

    Evidence (SPRINT33-C Phase 3 score distribution, docs/SPRINT33-C-
    phase3-score-distribution.md): 8.1% (33/409) of matched candidates in
    the Beta corpus were <=10 characters, and 63% of those were <=3
    characters — OCR-noise fragments a heading candidate coincidentally
    matched inside (e.g. a single merged Hangul syllable), not real
    headings. Note the arithmetic at default weights: heading(+100) +
    paragraph(+30) - tiny(-60) = 70, still >= DEFAULT_THRESHOLD(50) — this
    feature alone does NOT suppress a tiny candidate that also matches a
    heading; it only pulls a heading-less tiny paragraph (0+30-60=-30)
    further from threshold, which was already non-boundary. Whether the
    documented tiny OCR matches are actually filtered is an empirical
    question answered by re-running shadow_boundary_analysis.py, not by
    this docstring — see the Phase 4 implementation report."""

    def score(self, context: BoundaryContext) -> float:
        threshold = context.min_chunk_size or DEFAULT_MIN_CHUNK_SIZE
        return 1.0 if len(context.candidate_text.strip()) < threshold else 0.0


class SentenceBoundaryConfidenceFeature:
    """[SPRINT33-C Phase 4-B] Fires (1.0) when the candidate's last
    non-empty line ends like a complete sentence, via
    core.text_normalizer._ends_like_sentence — the exact primitive
    core.text_normalizer.collapse_soft_linebreaks already applies per-line
    (text_normalizer.py:99,102,109) to decide whether a short line should
    be merged into the previous one, reused here unchanged (no new
    detection logic, per HQ Phase 4-B scope: no sentence regex
    improvements).

    Known imprecision, inherited as-is (text_normalizer.py is out of
    scope): _RE_SENTENCE_END is not end-anchored, so a line with a
    mid-line period (e.g. a verse citation like "고전1:8-14 참고") can
    register as sentence-ending even when it isn't. Not corrected here —
    documented for Phase 5 calibration to weigh.

    Evidence (SPRINT33-C Phase 4-B Preflight, ad-hoc measurement over the
    full Beta corpus): 88.0% of all 16106 candidates and 85.1% of the 409
    heading-matched candidates already end like a sentence — a high base
    rate, so at the current +10 weight this feature has limited
    discriminative power (mirrors ParagraphBoundaryFeature's base-rate
    role, just not as extreme). HQ Phase 4-B decision keeps the positive
    formulation (+10, "ends like a sentence") rather than inverting it to
    a "cut mid-sentence" penalty — reconsider only in Phase 5."""

    def score(self, context: BoundaryContext) -> float:
        lines = [l for l in context.candidate_text.strip().splitlines() if l.strip()]
        if not lines:
            return 0.0
        return 1.0 if _ends_like_sentence(lines[-1]) else 0.0


class ScriptureReferenceBoundaryFeature:
    """[SPRINT33-C Phase 4-C] Fires (1.0) when core.retrieval.QueryParser
    finds a scripture reference within the candidate's first
    core.config.SCRIPTURE_REFERENCE_HEAD_WINDOW characters — deliberately
    NOT "anywhere in the candidate" (see module docstring and Phase 4-C
    overlap Preflight): most in-body citations occur mid-paragraph and are
    not boundary signals, only ones shaped like "REF + title" at the very
    start are. Reuses QueryParser exactly as core.tsu_builder._reference_
    parser already does for verse_mapping — no new reference grammar."""

    def score(self, context: BoundaryContext) -> float:
        head = context.candidate_text.strip()[:SCRIPTURE_REFERENCE_HEAD_WINDOW]
        if not head:
            return 0.0
        refs = _reference_parser.parse(head).scripture_refs
        return 1.0 if refs else 0.0


class EmbeddingSimilarityBoundaryFeature:
    """[ADR-008 제안 3, 2026-07-21] 인접 후보(현재 candidate_text vs
    BoundaryContext.previous_candidate_text) 임베딩(bge-m3,
    core/embedder.py 재사용 — 신규 임베딩 인프라 도입 없음)의 코사인
    유사도가 core.config.EMBEDDING_SIMILARITY_DROP_THRESHOLD 미만이면
    주제 전환으로 보고 1.0을 낸다. 업계 표준(LlamaIndex
    SemanticSplitterNodeParser 계열)인 "인접 문장 임베딩 유사도 급락"
    방식.

    ADR-008 §1 판정 배경: Profile B(학력 밀도 낮은 학술 주석서)의 Axis 2
    (semantic flush ratio) 실측 16.4%는 다른 구조·규칙 기반 5개
    feature(heading/paragraph/tiny_fragment/sentence_boundary/
    scripture_reference)가 heading이 드문 주석 문서에서 신호를 거의 못
    낸다는 뜻 — 이 feature는 구조와 무관하게 내용 자체의 주제 전환을
    잡아 그 공백을 메우기 위한 것이다.

    previous_candidate_text가 없거나(문서/버퍼 시작) 임베딩 호출이
    실패하면 신호 없음(0.0)으로 안전하게 폴백한다 — Ollama 장애 한 번이
    전체 Boundary Score 계산을 막지 않도록(다른 feature와 동일한 "raw
    signal 0.0=없음" 계약 유지)."""

    def __init__(self, embed_fn=None, drop_threshold: float = EMBEDDING_SIMILARITY_DROP_THRESHOLD):
        self._embed_fn = embed_fn or _embedder.embed
        self._drop_threshold = drop_threshold

    def score(self, context: BoundaryContext) -> float:
        prev = context.previous_candidate_text.strip()
        curr = context.candidate_text.strip()
        if not prev or not curr:
            return 0.0
        try:
            v_prev = self._embed_fn(prev)
            v_curr = self._embed_fn(curr)
        except Exception:
            return 0.0
        similarity = _cosine_similarity(v_prev, v_curr)
        return 1.0 if similarity < self._drop_threshold else 0.0


class PageHeaderArtifactFeature:
    """[ADR-011 제안 3, 2026-07-23] context.repetition_signal(호출자가
    문서 단위 core.repetition_detector.RepetitionTracker로 이미 관측한
    신호)이 반복으로 판정됐으면 1.0을 낸다 — registry에는 음의 weight
    (PAGE_HEADER_ARTIFACT_WEIGHT)로 등록해 "반복 감지됨 = boundary
    아님"을 표현한다(tiny_fragment와 동일 계열).

    repetition_signal이 없으면(호출자가 tracker를 제공하지 않음, 기존
    _default_registry() 사용부 포함) 신호 없음(0.0)으로 안전하게
    폴백한다 — 다른 feature와 동일한 계약."""

    def score(self, context: BoundaryContext) -> float:
        signal = context.repetition_signal
        if signal is None:
            return 0.0
        return 1.0 if signal.is_repeat else 0.0


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
    r.register("tiny_fragment", TinyFragmentPenaltyFeature(), weight=-60.0)
    r.register("sentence_boundary", SentenceBoundaryConfidenceFeature(), weight=10.0)
    r.register(
        "scripture_reference",
        ScriptureReferenceBoundaryFeature(),
        weight=SCRIPTURE_REFERENCE_WEIGHT,
    )
    r.register(
        "embedding_similarity",
        EmbeddingSimilarityBoundaryFeature(),
        weight=EMBEDDING_SIMILARITY_WEIGHT,
    )
    return r


def registry_with_page_header_artifact() -> FeatureRegistry:
    """[ADR-011 제안 3] Opt-in registry for measurement only — adds the
    7th feature on top of _default_registry()'s 6. NOT used by
    get_registry()/score_boundary()'s default path; callers that want
    PageHeaderArtifactFeature must request this explicitly and also pass
    a populated BoundaryContext.repetition_signal (see
    core.repetition_detector.RepetitionTracker). Kept separate from
    _default_registry() so production behavior stays unchanged until a
    separate HQ approval promotes this feature (ADR-011 Consequences)."""
    r = _default_registry()
    r.register(
        "page_header_artifact",
        PageHeaderArtifactFeature(),
        weight=PAGE_HEADER_ARTIFACT_WEIGHT,
    )
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
