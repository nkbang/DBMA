"""Knowledge score decomposition, replacing the single opaque `confidence` field.

Per the Phase 3 gate review: instead of one number pretending to summarize
everything, four independently-meaningful components plus a weighted overall:

- llm_score: the claim-extraction LLM's own self-reported confidence
  (claim.py). Still model self-reported and uncalibrated - this module does
  not change that, just relabels it so it isn't confused with the other
  three, which ARE independently checked.
- parser_score: a deterministic signal about candidate quality (sentence
  completeness, length) - not about whether the claim is *true*, only about
  whether the source sentence was a clean, well-formed candidate to begin
  with.
- evidence_score: fraction of listed scripture references that are
  syntactically well-formed (evidence.py). NOT a check that the passage
  textually supports the claim - see evidence.py's scope limitation.
- citation_score: fraction of listed citations independently re-verified
  against canonical.json footnotes/text (consistency.py).

overall_score is a weighted average over whichever components have a value
(missing components - e.g. no scriptures cited - are excluded and the
remaining weights renormalized, rather than assumed perfect). This is a
heuristic aggregate for triage/sorting, not a calibrated probability -
review_status stays "unverified" on every record regardless of overall_score.
"""
from __future__ import annotations

import re

from . import config, consistency, evidence

_TERMINAL_PUNCT = re.compile(r"[.!?]\s*$")


def parser_score(record: dict) -> float:
    text = (record.get("source_text") or "").strip()
    if not text:
        return 0.0
    score = 0.5
    if len(text) >= 40:
        score += 0.25
    if _TERMINAL_PUNCT.search(text):
        score += 0.25
    return round(min(score, 1.0), 3)


def evidence_score(record: dict) -> float | None:
    results = evidence.check_record_evidence(record)
    if not results:
        return None
    valid = sum(1 for r in results if r["format_valid"])
    return round(valid / len(results), 3)


def citation_score(record: dict) -> float | None:
    results = consistency.verify_citations(record)
    if not results:
        return None
    verified = sum(1 for v in results.values() if v)
    return round(verified / len(results), 3)


def compute_scores(record: dict) -> dict:
    llm = record.get("confidence")
    components = {
        "llm_score": llm,
        "parser_score": parser_score(record),
        "evidence_score": evidence_score(record),
        "citation_score": citation_score(record),
    }

    weighted_sum = 0.0
    weight_total = 0.0
    for name, value in components.items():
        if value is None:
            continue
        weight = config.SCORE_WEIGHTS[name]
        weighted_sum += value * weight
        weight_total += weight

    overall = round(weighted_sum / weight_total, 3) if weight_total > 0 else None

    return {**components, "overall_score": overall}
