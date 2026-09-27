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
from core.query_translation import contains_hangul, translate_to_english
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
    """USE_INVERTED_INDEX gates the Stage-1 CandidateGenerator path.
    [2026-09-18, 배포 성능 발견] Defaults to true — RetrievalEngine의 STEP 1/2가
    책 이름 없는 질의(교리/주제 질문, 가장 흔한 사용 패턴)에서 metadata filter가
    코퍼스 전체를 통과시켜 BM25가 O(N) 콜드 스캔을 하는 문제(84,766건 코퍼스에서
    쿼리 1건이 수 분 이상 걸림, 실측 확인)를 HybridQueryProcessor가 Tantivy
    역색인으로 우회한다(실측 14.3ms, 53,231건 코퍼스 기준). 필요 시
    USE_INVERTED_INDEX=false로 명시적으로 되돌릴 수 있다."""
    return os.environ.get("USE_INVERTED_INDEX", "true").strip().lower() == "true"


# 코퍼스의 한국어 비중이 이 값 미만이면 한글 질의를 Stage-1 전에 번역한다.
# 배포 기준선 실측값은 0.00%(119,595건 전량 영문)이고, 한국어 자료가 유의미하게
# 쌓이면(20% 이상) 번역 전처리는 자동으로 멈춘다.
_KOREAN_CORPUS_THRESHOLD = 0.20


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

    def _corpus_korean_ratio(self) -> float:
        """코퍼스에서 한국어 TSU가 차지하는 비율(1회 계산 후 캐시)."""
        cached = getattr(self, "_ko_ratio", None)
        if cached is None:
            total = len(self.tsu_by_id) or 1
            ko = sum(1 for t in self.tsu_by_id.values() if (t.get("language") or "") == "ko")
            cached = ko / total
            self._ko_ratio = cached
        return cached

    def _should_translate_upfront(self, query_text: str) -> bool:
        """한국어 질의를 Stage-1 **전에** 번역할지.

        [2026-09-26 설계 정정] 처음에는 "Stage-1이 0건일 때만 번역"으로 좁혔다.
        그 설계는 실패했다 — 한국어 토큰이 영문 코퍼스의 **OCR 잡음**에는
        걸리기 때문에 0건이 되지 않고, 따라서 번역이 영원히 발동하지 않는다.
        실측(P0-5 유보 17건): 구절 참조가 있는 5건이 번역 없이 후보를 얻었고
        그 내용은 전부 잡음이었다(OCR 쓰레기·성구 색인 페이지·거울상 OCR).

        그래서 발동 기준을 "결과가 비었는가"가 아니라 **"질의 언어와 코퍼스
        언어가 어긋났는가"**로 바꾼다. 코퍼스에 한국어가 거의 없으면(현 배포
        기준선은 정확히 0.00%) 한글 질의는 어휘 일치가 성립할 수 없으므로
        번역이 필수 전처리다. 코퍼스에 한국어 자료가 쌓이면 이 조건이 저절로
        거짓이 되어 번역이 멈춘다.
        """
        if not contains_hangul(query_text):
            return False
        return self._corpus_korean_ratio() < _KOREAN_CORPUS_THRESHOLD

    def _corpus_has_book_ids(self) -> bool:
        """코퍼스에 book_id가 하나라도 있는지(1회 계산 후 캐시).

        [2026-09-26] 배포 기준선 코퍼스 119,595건 중 verse_mapping을 가진 TSU가
        0건(0.0%)이다. 그런데 CandidateGenerator.search()는 질의에서 감지된
        책 이름을 `book_id` term 필터(Occur.Must)로 얹으므로, 이 코퍼스에서는
        **성경 책 이름이 들어간 모든 질의가 구조적으로 0건**이 된다.
          실측: "no condemnation in Christ Jesus"        -> 2건
                "Romans no condemnation in Christ Jesus" -> 0건 (ROM 감지)
        설교 준비 질의는 대개 책 이름을 포함하므로 영향이 넓다.

        해결은 "0건이면 필터를 버리고 재시도"가 아니다 — 그렇게 하면 필터 없는
        검색이 OCR 잡음을 후보로 채워 넣고(실측 확인), 그 결과 번역 폴백이
        발동하지 못해 정직한 0건보다 나빠진다. 필터가 **만족 불가능할 때만**
        애초에 얹지 않는 것이 정확한 처방이다.
        """
        cached = getattr(self, "_has_book_ids", None)
        if cached is None:
            cached = any(
                (t.get("verse_mapping") or {}).get("book_id")
                for t in self.tsu_by_id.values()
            )
            self._has_book_ids = cached
        return cached

    def _query_parser(self) -> QueryParser:
        """번역문 재파싱 전용. HybridQueryProcessor가 이미 parser를 갖지만
        HybridRetriever는 독립적으로 쓰이기도 해서(테스트·A/B) 자체 보유한다."""
        if getattr(self, "_parser_cached", None) is None:
            self._parser_cached = QueryParser()
        return self._parser_cached

    def _generate_candidates(
        self,
        parsed_query: ParsedQuery,
        candidate_k: int,
        file_scope: Optional[list[str]],
        telemetry_out: Optional[dict[str, Any]],
    ) -> list[CandidateRef]:
        """Stage 1 — route 분류 후 후보를 만든다. 번역 재시도가 같은 경로를
        다시 타야 하므로 메서드로 분리했다(로직 변경 없음)."""
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
            # [2026-09-26] Bible Index가 비어 있으면 자유 텍스트 검색으로 내려간다.
            # 실측: 배포 기준선 코퍼스 119,595건 중 verse_mapping을 가진 TSU가
            # 0건(0.0%)이라 bible_posting 테이블이 0행이다. 구절 참조가 들어간
            # 질의는 전부 이 route로 들어와 빈 포스팅 리스트를 받고 0건으로
            # 끝났는데, 설교 준비에서 가장 흔한 질의 형태가 바로 그것이다.
            # 포스팅 히트가 있으면 기존 동작이 그대로 유지되고(정확 참조 우선),
            # 없을 때만 내려가므로 0건보다 나빠질 수 없다.
            if not candidates:
                if telemetry_out is not None:
                    telemetry_out["route"] = "bible->hybrid"
                candidates = self.candidate_generator.search(
                    parsed_query, k=candidate_k, source_files=file_scope, with_snippets=False,
                    book_ids=None if self._corpus_has_book_ids() else [],
                )
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
                book_ids=None if self._corpus_has_book_ids() else [],
            )
        return candidates

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
        # [2026-09-26] 언어 불일치 전처리 — 결과가 빈 뒤가 아니라 **앞에서**
        # 번역한다(위 _should_translate_upfront 주석의 실패 근거 참고).
        if self._should_translate_upfront(parsed_query.original_query):
            translated = translate_to_english(parsed_query.original_query)
            if translated:
                parsed_query = self._query_parser().parse(translated)
                if telemetry_out is not None:
                    telemetry_out["translation_used"] = True
                    telemetry_out["translated_query"] = translated

        candidates = self._generate_candidates(
            parsed_query, candidate_k, file_scope, telemetry_out
        )

        # [2026-09-26] 한국어 질의 ↔ 영문 코퍼스 불일치 구제.
        # Stage-1이 어휘 일치이므로 한국어 토큰은 영문 본문과 교집합이 0이고,
        # 여기서 폴백이 없으면 그대로 0건으로 끝난다(실측: P0-5 유보 17건 중
        # 16건이 이 경로). 이미 후보를 찾은 질의는 건드리지 않으므로 빠른 경로의
        # 지연이 늘지 않는다 — 막다른 길에서만 번역을 시도한다.
        # 번역 실패 시 원래의 0건이 유지될 뿐이라 순손실이 없다.
        if not candidates and contains_hangul(parsed_query.original_query):
            translated = translate_to_english(parsed_query.original_query)
            if translated:
                translated_pq = self._query_parser().parse(translated)
                retried = self._generate_candidates(
                    translated_pq, candidate_k, file_scope, telemetry_out
                )
                if retried:
                    # Stage-2(신학·구절 점수)도 실제로 후보를 찾아낸 질의를
                    # 기준으로 계산한다 — 한국어 원문으로 영문 청크를 채점하면
                    # 후보는 번역문이 고르고 점수는 원문이 매기는 불일치가 된다.
                    parsed_query = translated_pq
                    candidates = retried
                    if telemetry_out is not None:
                        telemetry_out["translation_used"] = True
                        telemetry_out["translated_query"] = translated

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


class _EngineCompat:
    """[2026-09-18, USE_INVERTED_INDEX 기본 true 전환] core.retrieval.
    RetrievalEngine의 `.engine` 표면 중 UI가 직접 호출하는 3개 메서드/속성
    (list_source_files, book_coverage, tsus)만 HybridQueryProcessor 위에
    재현한다 — RetrievalEngine을 별도로 생성하지 않고 이미 로드된
    tsu_by_id를 재사용. ui/pages/chat.py:140, sermon_draft.py:159,186,538,
    sermon_research.py:149가 이 표면에 의존한다."""

    def __init__(self, tsu_by_id: dict[str, dict[str, Any]]) -> None:
        self.tsus = list(tsu_by_id.values())

    def list_source_files(self, registry_path: Optional[str] = None) -> list[str]:
        import os as _os
        from core.config import DEFAULT_REGISTRY_PATH

        registry_path = registry_path or DEFAULT_REGISTRY_PATH
        valid_sources: set[str] = set()
        if _os.path.exists(registry_path):
            from core.identity_registry import load_identity_registry
            registry = load_identity_registry(registry_path)
            for doc in registry.get("documents", {}).values():
                if (doc.get("ingest_status") == "PROCESSED"
                        and doc.get("superseded_by") is None):
                    sf = doc.get("source_file")
                    if sf:
                        valid_sources.add(sf)

        result = {sf for t in self.tsus if (sf := t.get("source_file"))}
        if _os.path.exists(registry_path):
            result &= valid_sources
        return sorted(result)

    def book_coverage(self) -> dict[str, int]:
        coverage: dict[str, set[str]] = {}
        for t in self.tsus:
            book_id = (t.get("verse_mapping") or {}).get("book_id")
            source_file = t.get("source_file")
            if not book_id or not source_file:
                continue
            coverage.setdefault(book_id, set()).add(source_file)
        return {book_id: len(files) for book_id, files in coverage.items()}


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
        self.engine = _EngineCompat(tsu_by_id)
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
    instead of kept as a list.

    [CI validate 실패 수정, 2026-09-18] tsu_dataset_path가 없으면 빈 dict를
    반환한다 — core/retrieval.py::RetrievalEngine._load_corpus()가 문서화한
    "파일 없음 = 첫 실행/초기화 직후의 정상 상태 → 빈 코퍼스" 계약과 동일.
    core/candidate_generator.py::build_index()에 이미 적용한 것과 같은 수정
    (e121752)을 이 호출부에도 적용 — HybridQueryProcessor.__init__()이
    open_or_build_index() 다음에 바로 이 함수를 호출해, 앞서 고친 크래시가
    막힌 뒤에도 여기서 그대로 재발했다."""
    import json
    from pathlib import Path

    tsu_by_id: dict[str, dict[str, Any]] = {}
    if not Path(tsu_dataset_path).exists():
        return tsu_by_id
    with open(tsu_dataset_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("$"):
                continue
            tsu = json.loads(line)
            tsu_by_id[tsu.get("tsu_id", "")] = tsu
    return tsu_by_id
