"""Citation consistency check: does a TSU record's citation actually appear
near the claim's source page in the item's canonical.json?

This is a deterministic re-check, independent of NAE.pipeline.tsu.citation's
candidate-generation step at build time - it re-derives the answer from
canonical.json directly, so it also catches drift or bugs between build time
and verify time (the same category of defect the Phase 1/2 live smoke tests
found), rather than trusting the TSU record's own citations field.
"""
from __future__ import annotations

import json
from pathlib import Path

from NAE.pipeline.tsu import citation as tsu_citation
from NAE.pipeline.tsu import config as tsu_config

from . import config


def _load_canonical(identifier: str, canonical_root: Path = tsu_config.CANONICAL_ROOT) -> dict | None:
    path = canonical_root / identifier / "canonical.json"
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def verify_citations(record: dict, *, canonical_root: Path = tsu_config.CANONICAL_ROOT) -> dict[str, bool]:
    """Return {citation_text: is_verified} for every citation listed on the record."""
    citations = record.get("citations", [])
    if not citations:
        return {}

    canonical_json = _load_canonical(record.get("identifier", ""), canonical_root)
    if canonical_json is None:
        return {c: False for c in citations}

    page = record.get("page", 0)
    footnotes = canonical_json.get("footnotes", [])
    nearby = set(tsu_citation.nearby_footnotes(page, footnotes, window=config.CITATION_PAGE_WINDOW))

    # Author-name citations are re-checked against the paragraph text itself,
    # not just footnotes, since NAE.pipeline.tsu.citation.extract_author_mentions
    # also scans paragraph body text.
    paragraph_text = ""
    for paragraph in canonical_json.get("paragraphs", []):
        if paragraph.get("index") == record.get("paragraph"):
            paragraph_text = paragraph.get("text", "")
            break
    author_mentions = set(tsu_citation.extract_author_mentions(paragraph_text))

    return {c: (c in nearby or c in author_mentions) for c in citations}
