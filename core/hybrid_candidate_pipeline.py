"""core/hybrid_candidate_pipeline.py — Stage 1 (CandidateGenerator) + Stage 2
(existing vector/theological scoring, reused unmodified) behind a feature
flag.

DBMA-SEARCH-INFRA-001 Phase 2-6 (docs/architecture/DBMA-SEARCH-INFRA-001-PHASE2-PLAN.md §2-6).

This is the integration point the plan calls for without touching
core/retrieval.py: CandidateGenerator (Tantivy) replaces RetrievalEngine's
STEP 1(metadata filter)+STEP 2(BM25 full-corpus scan) — Stage 2 scoring
(`compute_theological_score`/`compute_passage_match_score`) is imported and
reused exactly as RetrievalEngine.retrieve() uses it, not reimplemented.

Feature flag: `USE_INVERTED_INDEX=true` (env var) gates whether callers
should route through HybridRetriever instead of RetrievalEngine.
`HybridQueryProcessor` (below) is the drop-in replacement for
`core.retrieval.QueryProcessor`'s `.process()` interface, wired into
`ui/state/query_processor.py::get_shared_query_processor()` — the single
chokepoint both ui/pages/chat.py and ui/pages/research.py already call
through, so no UI file needed any change.
"""

from __future__ import annotations

import os
import time
from typing import Any, Optional

from dataclasses import asdict

from core.candidate_generator import CandidateGenerator, CandidateRef, open_or_build_index
from core.bible_index import BibleIndex
from core.query_planner import QueryPlan, classify
from core.rrf import reciprocal_rank_fusion
from core.search_cache import SearchResultCache, make_cache_key
from core.retrieval import (
    ParsedQuery,
    RankedCandidate,
    QueryParser,
    ContextAssembler,
    CitationBuilder,
    ResponseFormatter,
    PerformanceMetrics,
    ResponsePackage,
    compute_theological_score,
    compute_passage_match_score,
)


def is_enabled() -> bool:
    """USE_INVERTED_INDEX=true gates the Stage-1 CandidateGenerator path.
    Defaults to false — the existing RetrievalEngine path stays authoritative
    until this is explicitly turned on (HQ 원칙: 기존 경로와 나란히 유지)."""
    return os.environ.get("USE_INVERTED_INDEX", "false").strip().lower() == "true"


class HybridRetriever:
    """Stage 0 (Query Planner) -> Stage 1 (CandidateGenerator or Bible Index,
    depending on route) -> Stage 2 (reused scoring) -> ranked top-K. Mirrors
    RetrievalEngine.retrieve()'s STEP 3/4/5 scoring formula closely enough
    for direct A/B comparison, without importing or modifying RetrievalEngine
    itself.
    """

    def __init__(
        self,
        candidate_generator: CandidateGenerator,
        tsu_by_id: dict[str, dict[str, Any]],
        bible_index: Optional[BibleIndex] = None,
    ) -> None:
        self.candidate_generator = candidate_generator
        self.tsu_by_id = tsu_by_id
        self.bible_index = bible_index

    def retrieve(
        self,
        parsed_query: ParsedQuery,
        k_output: int = 10,
        candidate_k: int = 30,
        file_scope: Optional[list[str]] = None,
        telemetry_out: Optional[dict[str, Any]] = None,
    ) -> list[RankedCandidate]:
        """`file_scope`: same semantics as RetrievalEngine.retrieve()'s
        `file_scope` — an allowlist of exact `source_file` values — passed
        straight through to CandidateGenerator's `source_files` filter.

        `telemetry_out`: if given a dict, it is populated in-place with
        `route`, `candidate_count`, and `merge_time_ms` (Search Telemetry,
        HQ 제안 ⑨) — an out-param rather than a return-type change so this
        method's signature stays compatible with every existing caller/test.

        Stage 0 (core.query_planner.classify) decides how Stage 1 runs:
        - bible: looked up directly via the Bible Index posting list (no
          free-text query at all — also sidesteps a real bug found in
          Phase 2-6: a literal "Romans 5:1-10"-style string breaks Tantivy's
          query parser, since ":" is field-selector syntax there).
        - exact: Tantivy PhraseQuery (word order matters), via
          CandidateGenerator's `exact_phrase`.
        - metadata: CandidateGenerator restricted to title/author fields
          only, not full body content.
        - greek/hybrid: CandidateGenerator's default free-text search,
          unchanged from before the Query Planner existed.
        """
        plan = classify(parsed_query.original_query, parsed_query)
        if telemetry_out is not None:
            telemetry_out["route"] = plan.route
        candidate_tsu_ids: Optional[list[str]] = None

        if plan.route == "bible" and self.bible_index is not None:
            seen: set[str] = set()
            candidate_tsu_ids = []
            for ref in parsed_query.scripture_refs:
                for tsu_id in self.bible_index.lookup_scripture_ref(ref):
                    if tsu_id not in seen:
                        # [Bug fix] Respect file_scope the same way other routes do.
                        if file_scope is not None and (
                            self.tsu_by_id.get(tsu_id, {}).get("source_file") not in file_scope
                        ):
                            continue
                        seen.add(tsu_id)
                        candidate_tsu_ids.append(tsu_id)
            # bm25_score has no meaning for a posting-list hit — every match
            # is an equally exact reference match; Stage 2 (theological/
            # passage score) differentiates within this set.
            candidates = [
                CandidateRef(tsu_id=tid, bm25_score=1.0) for tid in candidate_tsu_ids[:candidate_k]
            ]
        elif plan.route == "exact":
            candidates = self.candidate_generator.search(
                parsed_query, k=candidate_k, source_files=file_scope,
                exact_phrase=plan.exact_phrase, with_snippets=False,
            )
        elif plan.route == "metadata":
            candidates = self.candidate_generator.search(
                parsed_query, k=candidate_k, source_files=file_scope,
                fields=["title", "author"], with_snippets=False,
            )
        else:  # "greek" or "hybrid" — default free-text search, unchanged
            candidates = self.candidate_generator.search(
                parsed_query, k=candidate_k, source_files=file_scope, with_snippets=False,
            )

        if telemetry_out is not None:
            telemetry_out["candidate_count"] = len(candidates)

        content_refs_cache: dict[int, list] = {}
        scored: list[tuple[str, dict, float, float, float]] = []
        for cand in candidates:
            tsu = self.tsu_by_id.get(cand.tsu_id)
            if tsu is None:
                continue

            theological_score, _ = compute_theological_score(
                parsed_query.original_query, tsu, content_refs_cache=content_refs_cache,
            )
            passage_score = compute_passage_match_score(
                parsed_query.scripture_refs, tsu.get("verse_mapping", {}),
            )
            scored.append((cand.tsu_id, tsu, cand.bm25_score, theological_score, passage_score))

        # [HQ 제안 ⑦] RRF instead of a fixed-weight sum (was 0.4*bm25 +
        # 0.4*theological + 0.2*passage). A weighted sum assumes each
        # signal's raw score is on a comparable scale and that those exact
        # weights are the right split — RRF needs neither: it only uses each
        # signal's relative rank order, which is why HQ calls it more stable
        # for mixing heterogeneous signals (originally framed as BM25 *
        # Vector, but the same instability applies to BM25/theological/
        # passage, which are on entirely different scales here).
        t_merge_start = time.perf_counter()
        bm25_ranking = [tsu_id for tsu_id, _, _, _, _ in sorted(scored, key=lambda s: -s[2])]
        theological_ranking = [tsu_id for tsu_id, _, _, _, _ in sorted(scored, key=lambda s: -s[3])]
        passage_ranking = [tsu_id for tsu_id, _, _, _, _ in sorted(scored, key=lambda s: -s[4])]
        rrf_scores = reciprocal_rank_fusion([bm25_ranking, theological_ranking, passage_ranking])
        if telemetry_out is not None:
            telemetry_out["merge_time_ms"] = (time.perf_counter() - t_merge_start) * 1000

        ranked: list[RankedCandidate] = []
        for tsu_id, tsu, bm25_score, theological_score, passage_score in scored:
            ranked.append(RankedCandidate(
                tsu_id=tsu_id,
                content=tsu.get("content", ""),
                metadata=tsu,
                bm25_score=bm25_score,
                theological_score=theological_score,
                passage_score=passage_score,
                final_score=rrf_scores.get(tsu_id, 0.0),
            ))

        ranked.sort(key=lambda r: (-r.final_score, r.tsu_id))
        return ranked[:k_output]


class HybridQueryProcessor:
    """Drop-in replacement for `core.retrieval.QueryProcessor`'s `.process()`
    interface — same signature, same `ResponsePackage` return type — routing
    through `HybridRetriever` instead of `RetrievalEngine`. Reuses
    `QueryParser`/`ContextAssembler`/`CitationBuilder`/`ResponseFormatter`
    from core.retrieval unmodified; only the retrieval step (Stage 1+2) is
    swapped.

    `PerformanceMetrics` only has `total_ms` populated here — CandidateGenerator/
    HybridRetriever don't yet break down per-stage timing the way
    RetrievalEngine's `retrieve()` does (vector_search_ms etc. stay 0.0).
    Good enough for the flag's initial rollout; per-stage timing can be
    added later without changing this class's interface.

    [HQ 제안 ⑥ Search Result Cache] Caches the ranked candidate LIST (Stage
    0-2 output) keyed on normalized query + k + file_scope + the current TSU
    dataset's manifest fingerprint — not the full ResponsePackage, since
    context/citation assembly is cheap and deterministic; the expensive part
    is retrieval, so that's the only part cached. A reindex changes the
    fingerprint, so stale cache rows become unreachable without a separate
    invalidation call.
    """

    def __init__(
        self,
        tsu_dataset_path: Optional[str] = None,
        candidate_index_dir: Optional[str] = None,
        bible_index_path: Optional[str] = None,
        telemetry_path: Optional[str] = None,
        cache_path: Optional[str] = None,
        tsu_manifest_path: Optional[str] = None,
        cache_ttl_seconds: float = 600.0,
    ) -> None:
        from core.config import (
            DEFAULT_BIBLE_INDEX_PATH,
            DEFAULT_CANDIDATE_INDEX_DIR,
            DEFAULT_SEARCH_CACHE_PATH,
            DEFAULT_SEARCH_TELEMETRY_PATH,
            DEFAULT_TSU_DATASET_PATH,
            DEFAULT_TSU_MANIFEST_PATH,
        )
        from core.bible_index import build_index as build_bible_index, _row_count
        from core.search_telemetry import SearchTelemetry
        from pathlib import Path

        tsu_dataset_path = tsu_dataset_path or DEFAULT_TSU_DATASET_PATH
        candidate_index_dir = candidate_index_dir or DEFAULT_CANDIDATE_INDEX_DIR
        bible_index_path = bible_index_path or DEFAULT_BIBLE_INDEX_PATH
        telemetry_path = telemetry_path or DEFAULT_SEARCH_TELEMETRY_PATH
        cache_path = cache_path or DEFAULT_SEARCH_CACHE_PATH
        self.tsu_manifest_path = tsu_manifest_path or DEFAULT_TSU_MANIFEST_PATH
        self.cache_ttl_seconds = cache_ttl_seconds

        generator = open_or_build_index(tsu_dataset_path, candidate_index_dir)
        tsu_by_id = load_tsu_by_id(tsu_dataset_path)
        bible_path = Path(bible_index_path)
        # Build BibleIndex if file doesn't exist OR has 0 rows (empty/stale index).
        # A bare file check misses the case where the file was created but never populated.
        if not bible_path.exists() or _row_count(bible_path) == 0:
            build_bible_index(tsu_dataset_path, bible_index_path)
        bible_index = BibleIndex(bible_index_path)
        self.retriever = HybridRetriever(generator, tsu_by_id, bible_index=bible_index)
        self.telemetry = SearchTelemetry(telemetry_path)
        self.cache = SearchResultCache(cache_path)

        self.parser = QueryParser()
        self.context_assembler = ContextAssembler()
        self.citation_builder = CitationBuilder()
        self.response_formatter = ResponseFormatter()

    def _dataset_fingerprint(self) -> Optional[str]:
        """Same manifest.dataset_sha256 read ui/state/query_processor.py
        already does for staleness detection — reused here as the cache
        key's index-version component, not duplicated logic (this is a
        second, independent read of the same manifest field, not a shared
        function, since core/ must not import from ui/)."""
        import json as _json
        from pathlib import Path as _Path

        manifest_path = _Path(self.tsu_manifest_path)
        if not manifest_path.exists():
            return None
        try:
            data = _json.loads(manifest_path.read_text(encoding="utf-8"))
            return data.get("dataset_sha256")
        except (_json.JSONDecodeError, OSError):
            return None

    def process(
        self,
        query: str,
        query_id: str = "",
        k: int = 10,
        file_scope: Optional[list[str]] = None,
    ) -> ResponsePackage:
        t_start = time.perf_counter()

        fingerprint = self._dataset_fingerprint()
        cache_key = make_cache_key(query, k, file_scope, fingerprint)
        cached_candidates = self.cache.get(cache_key)
        cache_hit = cached_candidates is not None

        parsed_query = self.parser.parse(query)
        telemetry_data: dict[str, Any] = {}
        if cache_hit:
            candidates = [RankedCandidate(**c) for c in cached_candidates]
            telemetry_data["route"] = "cache"
            telemetry_data["candidate_count"] = len(candidates)
            telemetry_data["merge_time_ms"] = 0.0
        else:
            candidates = self.retriever.retrieve(
                parsed_query, k_output=k, file_scope=file_scope, telemetry_out=telemetry_data,
            )
            self.cache.set(cache_key, [asdict(c) for c in candidates], ttl_seconds=self.cache_ttl_seconds)

        llm_context_block, scripture_contexts = self.context_assembler.assemble(candidates[:k], parsed_query)
        citations = self.citation_builder.build_citations(candidates[:k])

        total_ms = (time.perf_counter() - t_start) * 1000
        metrics = PerformanceMetrics(total_ms=total_ms)
        response = self.response_formatter.format(
            parsed_query, candidates[:k], scripture_contexts, llm_context_block, citations, metrics,
        )
        response.query_id = query_id

        # [HQ 제안 ⑨ Search Telemetry] Recorded for every call. cache_hit is
        # now real (HQ 제안 ⑥ wired in above) — embedding_time/ann_time stay
        # honestly 0 (see core/search_telemetry.py module docstring for why).
        # `telemetry_query_id` is set as a plain attribute (ResponsePackage
        # is a vanilla dataclass, not modified here) so a UI click handler
        # can correlate a later click back to this exact recorded query.
        query_record_id = self.telemetry.record_query(
            query_text=query,
            route=telemetry_data.get("route", "unknown"),
            result_count=len(candidates[:k]),
            candidate_count=telemetry_data.get("candidate_count", 0),
            latency_ms=total_ms,
            merge_time_ms=telemetry_data.get("merge_time_ms", 0.0),
            cache_hit=cache_hit,
        )
        response.telemetry_query_id = query_record_id
        return response


def load_tsu_by_id(tsu_dataset_path: str) -> dict[str, dict[str, Any]]:
    """Load the TSU dataset into an id-keyed dict for Stage 2 lookups —
    same file RetrievalEngine._load_corpus() reads, just indexed by tsu_id
    instead of kept as a list."""
    import json

    tsu_by_id: dict[str, dict[str, Any]] = {}
    with open(tsu_dataset_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("$"):
                continue
            tsu = json.loads(line)
            tsu_by_id[tsu.get("tsu_id", "")] = tsu
    return tsu_by_id
