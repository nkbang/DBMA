"""Load canonical.json (+ raw collector metadata) and build claim-candidate sentence records."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from . import citation, config, scripture


@dataclass
class SentenceCandidate:
    book: str
    author: str
    identifier: str
    page: int
    paragraph_index: int
    sentence_index: int
    text: str
    context_before: str
    context_after: str
    candidate_scriptures: list[str] = field(default_factory=list)
    candidate_citations: list[str] = field(default_factory=list)


def _find_raw_metadata(identifier: str, raw_root: Path = config.RAW_ROOT) -> dict:
    if not raw_root.exists():
        return {}
    for category_dir in raw_root.iterdir():
        candidate = category_dir / identifier / "metadata.json"
        if candidate.exists():
            with open(candidate, encoding="utf-8") as fh:
                return json.load(fh)
    return {}


def load_canonical(identifier: str, canonical_root: Path = config.CANONICAL_ROOT) -> dict | None:
    path = canonical_root / identifier / "canonical.json"
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def build_candidates(identifier: str, *, canonical_root: Path = config.CANONICAL_ROOT,
                      raw_root: Path = config.RAW_ROOT) -> list[SentenceCandidate]:
    canonical_json = load_canonical(identifier, canonical_root)
    if canonical_json is None:
        return []

    raw_meta = _find_raw_metadata(identifier, raw_root)
    book = raw_meta.get("title", "") or identifier
    author = raw_meta.get("creator", "")
    footnotes = canonical_json.get("footnotes", [])

    candidates: list[SentenceCandidate] = []
    for paragraph in canonical_json.get("paragraphs", []):
        if paragraph.get("type") != "prose":
            continue
        sentences = paragraph.get("sentences", [])
        page = paragraph.get("page_start", 0)

        para_scriptures = scripture.extract_for_sentence(paragraph.get("text", ""))
        para_authors = citation.extract_author_mentions(paragraph.get("text", ""))
        para_footnotes = citation.nearby_footnotes(page, footnotes)
        candidate_citations = sorted(set(para_authors) | set(para_footnotes))

        for i, sent in enumerate(sentences):
            text = sent.get("text", "")
            if len(text) < config.MIN_CLAIM_SENTENCE_CHARS:
                continue
            before = sentences[i - 1]["text"] if i > 0 else ""
            after = sentences[i + 1]["text"] if i + 1 < len(sentences) else ""
            sentence_scriptures = scripture.extract_for_sentence(text) or para_scriptures

            candidates.append(SentenceCandidate(
                book=book,
                author=author,
                identifier=identifier,
                page=page,
                paragraph_index=paragraph.get("index", 0),
                sentence_index=i,
                text=text,
                context_before=before,
                context_after=after,
                candidate_scriptures=sentence_scriptures,
                candidate_citations=candidate_citations,
            ))
    return candidates
