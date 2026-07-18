"""
core/noise_classifier.py — Chunk-level noise type classifier (SPRINT28-B).

Classifier, not a deleter. classify() only labels a chunk of text with a
noise_type/policy/quality_score; it never mutates or removes content. The
resulting labels are consumed additively by core/tsu_builder.py as
TSU.content_quality metadata — core/retrieval.py does not read this field
yet (SPRINT28-B scope explicitly excludes any retrieval-side change).

Reuses existing signal functions rather than reimplementing them:
  - detect_paragraph_language() (core/text_normalizer.py) for the same
    Hebrew/Greek protection logic core/chunking_optimizer.py already uses,
    so ORIGINAL_LANGUAGE classification here agrees with what the chunker
    already protects from MIN_CHUNK_CHARS truncation.
  - calculate_noise_score() (core/utils.py) for OCR/symbol-ratio noise,
    instead of a second independent noise metric.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from core.text_normalizer import detect_paragraph_language
from core.utils import calculate_noise_score

NoiseType = Literal[
    "PAGE_NUMBER",
    "HEADER_FOOTER",
    "BIBLIOGRAPHY",
    "ABBREVIATION",
    "OCR_FRAGMENT",
    "ORIGINAL_LANGUAGE",
    "NORMAL_CONTENT",
]

Policy = Literal["REMOVE", "PRESERVE", "DOWNWEIGHT", "NORMAL"]

# [SPRINT28-B] Policy per noise type, per the CUE Execution Order:
#   REMOVE: PAGE_NUMBER, HEADER_FOOTER
#   PRESERVE: ORIGINAL_LANGUAGE
#   DOWNWEIGHT: BIBLIOGRAPHY, OCR_FRAGMENT
# ABBREVIATION's policy was not specified in the order — mapped to
# DOWNWEIGHT here (same rationale as BIBLIOGRAPHY: low search value but not
# certainly worthless, so a reversible ranking penalty rather than removal).
# This mapping does not remove anything itself — see module docstring.
_POLICY_BY_TYPE: dict[NoiseType, Policy] = {
    "PAGE_NUMBER": "REMOVE",
    "HEADER_FOOTER": "REMOVE",
    "BIBLIOGRAPHY": "DOWNWEIGHT",
    "ABBREVIATION": "DOWNWEIGHT",
    "OCR_FRAGMENT": "DOWNWEIGHT",
    "ORIGINAL_LANGUAGE": "PRESERVE",
    "NORMAL_CONTENT": "NORMAL",
}

_QUALITY_SCORE_BY_POLICY: dict[Policy, float] = {
    "REMOVE": 0.0,
    "DOWNWEIGHT": 0.3,
    "NORMAL": 1.0,
    "PRESERVE": 1.0,
}

# [SPRINT28-B] section_type is a coarser, TSU-facing label derived
# deterministically from noise_type — not an independent classifier (no
# separate "commentary vs sermon vs lexicon" document-type model; that is
# SPRINT28-D scope per the SPRINT28-A design proposal).
_SECTION_TYPE_BY_NOISE_TYPE: dict[NoiseType, str] = {
    "PAGE_NUMBER": "boilerplate",
    "HEADER_FOOTER": "boilerplate",
    "BIBLIOGRAPHY": "bibliography",
    "ABBREVIATION": "abbreviation",
    "OCR_FRAGMENT": "ocr_fragment",
    "ORIGINAL_LANGUAGE": "original_language_note",
    "NORMAL_CONTENT": "body",
}

_RE_PAGE_NUMBER_ONLY = re.compile(r"^\s*(?:page\s+)?\d+\s*$", re.IGNORECASE)

# Bibliography citation shape: an author/year parenthetical, e.g.
# "(Dillard, 1987)" or "(Leiden: E. J. Brill, 1974)".
_RE_CITATION_YEAR = re.compile(r"\(\s*[^()]*\b(?:19|20)\d{2}\b[^()]*\)")

# Abbreviation-list shape: a run of short (2-6 letter) all-caps tokens —
# the structural signature of an abbreviations/sigla page (e.g. "KHAT
# Kurzer Handcommentar zum Alten Testament KVHS Korte verklaring...",
# Beta Corpus Validation finding).
_RE_CAPS_TOKEN = re.compile(r"\b[A-Z]{2,6}\b")

# [SPRINT28-B] Best-effort only. Reliable header/footer detection requires
# cross-page repetition frequency (SPRINT28-A §3 "Header/Footer Intelligence
# Layer", deferred to SPRINT28-C) — this function sees one chunk's text in
# isolation, so it can only catch a narrow single-chunk shape: several very
# short, punctuation-less lines (byline/title-block style) with no sentence
# structure. Most real headers/footers never survive as standalone TSU
# chunks anyway, since core/chunking_optimizer.py's MIN_CHUNK_CHARS (80)
# merges short lines into surrounding paragraphs before a chunk is emitted.
_RE_SENTENCE_PUNCT = re.compile(r"[.!?。！？]")


def _looks_like_byline_block(text: str) -> bool:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not (1 <= len(lines) <= 4):
        return False
    if any(len(ln) > 48 for ln in lines):
        return False
    if any(_RE_SENTENCE_PUNCT.search(ln) for ln in lines):
        return False
    return True


def _caps_token_density(text: str) -> float:
    words = text.split()
    if not words:
        return 0.0
    return len(_RE_CAPS_TOKEN.findall(text)) / len(words)


@dataclass(frozen=True)
class NoiseClassification:
    noise_type: NoiseType
    policy: Policy
    quality_score: float
    section_type: str


def classify(text: str) -> NoiseClassification:
    """Classify a chunk of text into a NoiseType with its policy label.

    Read-only: never modifies `text`. Order matters — checks run from the
    most specific/protective signal (original-language protection, must
    never be shadowed by a noisier-looking classification) to the most
    generic fallback (NORMAL_CONTENT).
    """
    content = text or ""
    stripped = content.strip()

    if not stripped:
        return _result("PAGE_NUMBER")  # empty chunk — no searchable content

    # 1. Original-language protection first, matching the same signal
    #    core/chunking_optimizer.py already uses to exempt short Hebrew/
    #    Greek insertions from length-based filtering.
    lang = detect_paragraph_language(stripped)
    if lang.has_original_language:
        return _result("ORIGINAL_LANGUAGE")

    # 2. Exact page-number-only chunk.
    if _RE_PAGE_NUMBER_ONLY.match(stripped):
        return _result("PAGE_NUMBER")

    # 3. Bibliography citation shape (author/year parenthetical present).
    if _RE_CITATION_YEAR.search(stripped):
        return _result("BIBLIOGRAPHY")

    # 4. Abbreviation-list shape (dense run of short all-caps tokens,
    #    without the year-parenthetical citation shape checked above).
    if _caps_token_density(stripped) >= 0.08:
        return _result("ABBREVIATION")

    # 5. OCR/garble noise — reuse the existing symbol-ratio noise scorer
    #    rather than a second independent metric.
    noise = calculate_noise_score(stripped, file_type="txt")
    if noise.get("score", 0.0) >= 60.0:
        return _result("OCR_FRAGMENT")

    # 6. Best-effort single-chunk header/footer shape (see docstring above
    #    _looks_like_byline_block — full detection deferred to SPRINT28-C).
    if _looks_like_byline_block(stripped):
        return _result("HEADER_FOOTER")

    return _result("NORMAL_CONTENT")


def _result(noise_type: NoiseType) -> NoiseClassification:
    policy = _POLICY_BY_TYPE[noise_type]
    return NoiseClassification(
        noise_type=noise_type,
        policy=policy,
        quality_score=_QUALITY_SCORE_BY_POLICY[policy],
        section_type=_SECTION_TYPE_BY_NOISE_TYPE[noise_type],
    )
