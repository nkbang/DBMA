"""core/query_planner.py — Stage 0 rule-based Query Planner.

DBMA-SEARCH-INFRA-001 (HQ 추가 제안 ④). Classifies a raw query into one of
five routes BEFORE Stage 1 candidate generation runs, purely with regex/
Unicode-range rules — **no LLM call anywhere in this module** (HQ 원칙 3:
검색 경로에서는 LLM 호출을 금지할 것).

Routes:
    bible    — a scripture reference was detected (reuses core.retrieval's
               existing ScriptureReference parsing, not reimplemented) ->
               core/bible_index.py posting-list lookup, bypassing free-text
               BM25 entirely. This is also a correctness fix, not just a
               speed one: Phase 2-6 found that passing a literal
               "Romans 5:1-10"-style string into Tantivy's query parser
               raises a ValueError (":" is field-selector syntax there) —
               routing scripture refs around free-text search avoids that
               class of query entirely.
    greek    — Greek or Hebrew script detected (Unicode range check).
    exact    — the query is a quoted phrase ("..." or '...') -> Tantivy
               PhraseQuery (word order matters), not the default OR-tokenized
               query.
    metadata — a single capitalized Latin-script token (HQ example: "Calvin")
               -> restricted to title/author fields, not full body content,
               so a short proper-noun-like token doesn't broadly match every
               document's body text.
    hybrid   — everything else (the default/fallback — natural-language
               questions, thematic queries, including short Korean phrases
               like HQ's own "고난 속 소망" example).

`metadata`'s rule is intentionally narrow and structural ("this looks like a
single name-shaped token"), not a claim about what the term actually names —
there is no hand-typed author/name gazetteer here (inventing one would
violate the project's "never invent" data principle). Anything that doesn't
match falls through to `hybrid`, where BM25 over title/author/content still
finds real author-name matches anyway.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from core.retrieval import ParsedQuery

_GREEK_RE = re.compile(r"[Ͱ-Ͽἀ-῿]")
_HEBREW_RE = re.compile(r"[֐-׿]")

# Matches a query fully wrapped in a single pair of straight or curly quotes.
_QUOTED_RE = re.compile(r'^\s*["“”](.+)["”“]\s*$|^\s*\'(.+)\'\s*$')

# "metadata" route is intentionally narrow: a single Latin-script
# capitalized token (HQ example: "Calvin"). Word count alone can't
# distinguish an author-name lookup from a short THEMATIC phrase (HQ's own
# example "고난 속 소망" is 3 Korean words and routes to hybrid, not
# metadata) — and there is no author/name gazetteer to match against
# (inventing one would violate the project's "never invent" data
# principle), so this stays conservative: only unambiguously name-shaped
# queries route here, everything else falls through to hybrid, where BM25
# over title/author/content still finds real author-name matches anyway.
_PROPER_NOUN_RE = re.compile(r"^[A-Z][a-zA-Z'\-]*$")


@dataclass
class QueryPlan:
    route: str  # "bible" | "greek" | "exact" | "metadata" | "hybrid"
    reason: str
    exact_phrase: Optional[str] = None

    def to_dict(self) -> dict[str, object]:
        return {"route": self.route, "reason": self.reason, "exact_phrase": self.exact_phrase}


def classify(query_text: str, parsed_query: ParsedQuery) -> QueryPlan:
    """Classify `query_text` into a route. `parsed_query` must be the
    QueryParser().parse(query_text) result for the same text — this
    function does not re-run scripture detection itself, it reuses
    `parsed_query.scripture_refs`."""
    if parsed_query.scripture_refs:
        return QueryPlan(route="bible", reason="scripture reference detected")

    if _GREEK_RE.search(query_text):
        return QueryPlan(route="greek", reason="Greek script detected")
    if _HEBREW_RE.search(query_text):
        return QueryPlan(route="greek", reason="Hebrew script detected")

    quoted = _QUOTED_RE.match(query_text)
    if quoted:
        phrase = quoted.group(1) or quoted.group(2)
        return QueryPlan(route="exact", reason="quoted phrase", exact_phrase=phrase.strip())

    words = query_text.strip().split()
    if len(words) == 1 and _PROPER_NOUN_RE.match(words[0]):
        return QueryPlan(route="metadata", reason="single capitalized proper-noun-like token (author/tag-like)")

    return QueryPlan(route="hybrid", reason="default — natural language / thematic query")
