"""Sentence-level citation candidate detection.

Deterministic, rule-based - matches known author names (config.KNOWN_AUTHORS,
sourced from the Phase 1 collector's Priority-B keyword list) and pulls
footnote text already extracted by the Phase 2 canonical pipeline. This
evidence is passed to the LLM as candidates for it to confirm/use, rather
than asking the LLM to invent citations from scratch.
"""
from __future__ import annotations

import re

from . import config

_AUTHOR_PATTERNS = [
    (author, re.compile(r"\b" + re.escape(author) + r"\b"))
    for author in config.KNOWN_AUTHORS
]


def extract_author_mentions(text: str) -> list[str]:
    return sorted({author for author, pattern in _AUTHOR_PATTERNS if pattern.search(text)})


def nearby_footnotes(page: int, footnotes: list[dict], *, window: int = 1) -> list[str]:
    """Footnotes on the same page (or within `window` pages) as a candidate citation source."""
    return [
        fn["text"] for fn in footnotes
        if isinstance(fn.get("page"), int) and abs(fn["page"] - page) <= window
    ]
