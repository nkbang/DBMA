"""core/candidate_generator.py — Stage 1 Candidate Generator (Tantivy-backed BM25).

DBMA-SEARCH-INFRA-001 Phase 2-2 (docs/architecture/DBMA-SEARCH-INFRA-001-PHASE2-PLAN.md).

Logos-style two-stage retrieval, Stage 1 only: BM25 + metadata pre-filter over
an inverted index, returning id+score candidates — never full_text (Phase0/1
baseline showed the current RetrievalEngine.retrieve() STEP 1/2 scans the
entire corpus per query when metadata filtering fails to narrow the pool;
this module replaces that scan with a real index, engine = Tantivy per
C1-TASK-ORDER-033-REPORT.md).

This module is additive: it does not import from or modify core/retrieval.py's
RetrievalEngine, and RetrievalEngine is not touched by this change. Wiring
CandidateGenerator into the live retrieve() path behind a feature flag is
Phase 2-6, not this module.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import tantivy

from core.retrieval import ParsedQuery

# Text fields searched for BM25 candidate generation.
_TEXT_FIELDS = ["title", "content", "author"]

# Metadata fields stored with the "raw" tokenizer so they support exact-match
# term filtering (Stage 1 pre-filter — HQ principle: filters apply before
# candidate generation, not after).
_RAW_FIELDS = ["tsu_id", "document_id", "source_file", "book_id", "language"]


@dataclass
class CandidateRef:
    """A single Stage-1 candidate: id + score + the metadata needed for
    Stage 2 lookup — no `content` field. Search list responses must not
    carry full_text (HQ directive §3 "금지 사항").

    `snippet`/`highlight_ranges` ARE populated by default (Phase 2-5) — a
    short highlighted window is exactly what the HQ search-list response
    schema calls for (§3 example: `"snippet": "..."`), distinct from full_text.
    `highlight_ranges` are (start, end) Python string character offsets into
    `snippet` (not the original document, and not raw Tantivy byte offsets —
    those are UTF-8 byte positions and would misalign on any multi-byte
    text; converted here) marking matched-term spans, for the UI to bold
    without re-scanning the fragment itself.
    """

    tsu_id: str
    bm25_score: float
    book_id: str = ""
    source_file: str = ""
    language: str = ""
    snippet: str = ""
    highlight_ranges: list[tuple[int, int]] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "tsu_id": self.tsu_id,
            "bm25_score": round(self.bm25_score, 4),
            "book_id": self.book_id,
            "source_file": self.source_file,
            "language": self.language,
            "snippet": self.snippet,
            "highlight_ranges": [list(r) for r in self.highlight_ranges],
        }


def build_schema() -> tantivy.Schema:
    """TSU field mapping — same shape as scripts/bench_search_engines/tantivy_bench.py's
    schema, plus tokenizer_name='raw' on filter fields so exact term queries work."""
    sb = tantivy.SchemaBuilder()
    sb.add_text_field("title", stored=True)
    sb.add_text_field("content", stored=True)
    sb.add_text_field("author", stored=True)
    sb.add_text_field("tsu_id", stored=True, tokenizer_name="raw")
    sb.add_text_field("document_id", stored=True, tokenizer_name="raw")
    sb.add_text_field("source_file", stored=True, tokenizer_name="raw")
    sb.add_text_field("book_id", stored=True, tokenizer_name="raw")
    sb.add_text_field("language", stored=True, tokenizer_name="raw")
    sb.add_integer_field("page", stored=True)
    return sb.build()


def _tsu_to_tantivy_doc(tsu: dict, schema: tantivy.Schema) -> tantivy.Document:
    doc = tantivy.Document()
    doc.add_text("title", tsu.get("title") or "")
    doc.add_text("content", tsu.get("content") or "")
    doc.add_text("author", tsu.get("author") or "")
    doc.add_text("tsu_id", tsu.get("tsu_id", ""))
    doc.add_text("document_id", tsu.get("document_id") or "")
    doc.add_text("source_file", tsu.get("source_file") or "")
    doc.add_text("book_id", (tsu.get("verse_mapping") or {}).get("book_id") or "")
    doc.add_text("language", tsu.get("language") or "")
    doc.add_integer("page", tsu.get("page") or 0)
    return doc


def build_index(tsu_dataset_path: str | Path, index_dir: str | Path) -> int:
    """Build a fresh Tantivy index from a TSU JSONL dataset. Returns the
    number of documents indexed. Overwrites any existing index at index_dir."""
    index_dir = Path(index_dir)
    index_dir.mkdir(parents=True, exist_ok=True)
    schema = build_schema()
    idx = tantivy.Index(schema, str(index_dir))
    writer = idx.writer()
    # [bug fix] tantivy.Index(schema, path) re-opens an existing index dir
    # rather than truncating it, and add_document() only appends — so a
    # second build_index() call on the same dir left every previous
    # document (old tsu_id, stale content) permanently in the index
    # alongside the new ones, despite this function's docstring claiming
    # to overwrite. Confirmed: after two builds, a re-processed document's
    # old tsu_id (no longer in tsu_by_id) still matched queries, causing
    # HybridRetriever to silently drop those hits (tsu_by_id.get() -> None)
    # and return 0 results. delete_all_documents() actually clears the
    # index before this build's documents are added.
    writer.delete_all_documents()

    count = 0
    with open(tsu_dataset_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("$"):
                continue
            tsu = json.loads(line)
            writer.add_document(_tsu_to_tantivy_doc(tsu, schema))
            count += 1
    writer.commit()
    idx.reload()
    return count


def open_or_build_index(tsu_dataset_path: str | Path, index_dir: str | Path) -> "CandidateGenerator":
    """Open the Tantivy index at `index_dir`, building it from
    `tsu_dataset_path` first if it doesn't exist yet (bootstrap case — first
    call in a fresh environment, before any rebuild_tsu_index() has run)."""
    index_dir = Path(index_dir)
    if not (index_dir / "meta.json").exists():
        build_index(tsu_dataset_path, index_dir)
    return CandidateGenerator(index_dir)


class CandidateGenerator:
    """Stage 1 of the two-stage retrieval pipeline: BM25 + metadata
    pre-filter over a Tantivy index, returning capped id+score candidates.

    Stage 2 (semantic ranking / RRF merge / cross-encoder) is out of scope
    for this class — see DBMA-SEARCH-INFRA-001-PHASE2-PLAN.md §2-2/§2-3.
    """

    def __init__(self, index_dir: str | Path) -> None:
        self.index_dir = Path(index_dir)
        self._index = tantivy.Index.open(str(self.index_dir))
        self._schema = self._index.schema

    def search(
        self,
        parsed_query: ParsedQuery,
        k: int = 100,
        book_ids: Optional[list[str]] = None,
        source_files: Optional[list[str]] = None,
        with_snippets: bool = True,
        snippet_max_chars: int = 200,
        fields: Optional[list[str]] = None,
        exact_phrase: Optional[str] = None,
    ) -> list[CandidateRef]:
        """Return up to `k` candidates ranked by Tantivy's BM25 score.

        Metadata filters (book_ids/source_files, or parsed_query.detected_books
        when book_ids is not given) are applied as term filters combined with
        the text query via a Must-boolean query — i.e. before ranking, not
        after (HQ principle: 필터는 후보 생성 전 적용).

        `fields`: restrict which text fields the free-text query matches
        against (default `_TEXT_FIELDS` = title/content/author) — the Query
        Planner's "metadata" route (Phase 3) uses `fields=["title","author"]`
        so a short proper-noun-like query (e.g. an author name) doesn't match
        broadly across every document's body content, mirroring HQ's
        "메타데이터 인덱스" concept without a separate index.

        `exact_phrase`: when given, use a Tantivy PhraseQuery (slop=0) instead
        of the default OR-tokenized `parse_query()` — the Query Planner's
        "exact" route (quoted query text) for word-order-sensitive matches.

        [Phase 2-5] Snippets are generated from Tantivy's own SnippetGenerator
        for the k candidates returned — not by storing separate preview/
        highlight fields at index time, and not by re-reading the source
        document: `content` is already a stored Tantivy field fetched via
        `searcher.doc(addr)` regardless, so the snippet window comes from
        data already in hand. Cost scales with k (capped), never with corpus
        size. Set with_snippets=False to skip when only ids/scores are needed
        (e.g. an internal reranking pass that will fetch snippets later for
        just the final top-N).
        """
        self._index.reload()
        searcher = self._index.searcher()

        query_text = (exact_phrase or parsed_query.original_query).strip()
        if not query_text:
            return []

        search_fields = fields or _TEXT_FIELDS
        if exact_phrase:
            words = exact_phrase.strip().split()
            text_query = tantivy.Query.phrase_query(self._schema, "content", words)
        else:
            text_query = self._index.parse_query(query_text, default_field_names=search_fields)

        effective_books = book_ids if book_ids is not None else parsed_query.detected_books
        subqueries = [(tantivy.Occur.Must, text_query)]

        if effective_books:
            book_filters = [
                (tantivy.Occur.Should, tantivy.Query.term_query(self._schema, "book_id", b))
                for b in effective_books
            ]
            subqueries.append((tantivy.Occur.Must, tantivy.Query.boolean_query(book_filters)))

        if source_files:
            file_filters = [
                (tantivy.Occur.Should, tantivy.Query.term_query(self._schema, "source_file", sf))
                for sf in source_files
            ]
            subqueries.append((tantivy.Occur.Must, tantivy.Query.boolean_query(file_filters)))

        metadata_filters = subqueries[1:]  # book/source_file Must-clauses, if any
        query = subqueries[0][1] if len(subqueries) == 1 else tantivy.Query.boolean_query(subqueries)

        result = searcher.search(query, k)

        # [Phase 2-6 회귀 검증에서 발견] text AND metadata-filter can be a
        # genuine empty intersection — not a bug, a real case (e.g. an
        # all-English commentary volume queried in Korean: the metadata
        # filter matches real documents, but none of them contain any of the
        # query's tokens). RetrievalEngine.retrieve() has an equivalent
        # BM25-miss fallback (capped to candidate_k per the Phase 1 fix) so
        # Stage 2 scoring still gets *some* candidates instead of a dead
        # end; CandidateGenerator needs the same rescue or it silently loses
        # recall on every filtered-but-language-mismatched query (measured:
        # 12/96 book-level gold standard queries, all for all-English-source
        # books). Retry with metadata filters ONLY, still capped at k — no
        # full-corpus scan either way.
        if not result.hits and metadata_filters:
            fallback_query = (
                metadata_filters[0][1] if len(metadata_filters) == 1
                else tantivy.Query.boolean_query(metadata_filters)
            )
            result = searcher.search(fallback_query, k)

        snippet_generator = None
        if with_snippets and result.hits:
            snippet_generator = tantivy.SnippetGenerator.create(searcher, text_query, self._schema, "content")
            snippet_generator.set_max_num_chars(snippet_max_chars)

        candidates: list[CandidateRef] = []
        for score, addr in result.hits:
            doc = searcher.doc(addr)
            stored = doc.to_dict()

            snippet_text = ""
            highlight_ranges: list[tuple[int, int]] = []
            if snippet_generator is not None:
                snippet = snippet_generator.snippet_from_doc(doc)
                snippet_text = snippet.fragment()
                # tantivy's Range.start/end are UTF-8 BYTE offsets into the
                # fragment, not Python str character indices — off by a lot
                # for any multi-byte text (Korean/CJK). Convert so callers
                # can slice `snippet_text[start:end]` directly.
                frag_bytes = snippet_text.encode("utf-8")
                highlight_ranges = [
                    (len(frag_bytes[: r.start].decode("utf-8")), len(frag_bytes[: r.end].decode("utf-8")))
                    for r in snippet.highlighted()
                ]

            candidates.append(
                CandidateRef(
                    tsu_id=_first(stored, "tsu_id"),
                    bm25_score=float(score),
                    book_id=_first(stored, "book_id"),
                    source_file=_first(stored, "source_file"),
                    language=_first(stored, "language"),
                    snippet=snippet_text,
                    highlight_ranges=highlight_ranges,
                )
            )
        return candidates

    def reindex_document(self, tsus: list[dict]) -> int:
        """Incremental index update for a single document's TSUs — delete any
        existing rows for these tsu_ids, then re-add. Used when the caller
        already knows the exact tsu_ids being replaced (e.g. tests)."""
        writer = self._index.writer()
        for tsu in tsus:
            writer.delete_documents("tsu_id", tsu.get("tsu_id", ""))
        for tsu in tsus:
            writer.add_document(_tsu_to_tantivy_doc(tsu, self._schema))
        writer.commit()
        self._index.reload()
        return len(tsus)

    def replace_document(self, document_id: str, new_tsus: list[dict]) -> int:
        """Delete ALL rows for `document_id` (regardless of tsu_id/chunk
        count — a re-chunked document can produce a different set of tsu_ids
        than before) and add `new_tsus` in their place. This is what
        core/index_orchestrator.py::reindex_document() calls — the TSU
        dataset side already does exactly this same delete-by-document_id +
        re-add pattern (see its `kept = [r for r in existing if
        r.get("document_id") != document_id]`), so the index stays in sync
        with the dataset using the same replace semantics.

        Returns the number of new TSUs added.
        """
        writer = self._index.writer()
        writer.delete_documents("document_id", document_id)
        for tsu in new_tsus:
            writer.add_document(_tsu_to_tantivy_doc(tsu, self._schema))
        writer.commit()
        self._index.reload()
        return len(new_tsus)

    def delete_document(self, document_id: str) -> None:
        """Remove all rows for `document_id` without replacement — used for
        exclude/superseded-purge flows (core/index_orchestrator.py's
        exclude_document_from_index()/reconcile_pending())."""
        writer = self._index.writer()
        writer.delete_documents("document_id", document_id)
        writer.commit()
        self._index.reload()


def _first(stored: dict, field_name: str) -> str:
    values = stored.get(field_name) or [""]
    return values[0] if values else ""
