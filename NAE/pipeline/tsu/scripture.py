"""Sentence-level scripture reference extraction.

Deterministic, rule-based - reuses the same canonicalization logic already
validated in the Phase 2 canonical pipeline (NAE.pipeline.canonical.annotate),
rather than re-implementing or delegating this to the LLM.
"""
from __future__ import annotations

from NAE.pipeline.canonical.annotate import find_scripture_references_extended


def extract_for_sentence(text: str) -> list[str]:
    """Return canonical scripture references (e.g. 'John 3:16') found in a sentence."""
    refs = find_scripture_references_extended(text)
    return sorted({r["canonical"] for r in refs})
