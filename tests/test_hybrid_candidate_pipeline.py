"""Tests for core/hybrid_candidate_pipeline.py (DBMA-SEARCH-INFRA-001 Phase 2-6)."""

import json
import os

import pytest

from core.bible_index import BibleIndex
from core.candidate_generator import CandidateGenerator, build_index
from core.hybrid_candidate_pipeline import HybridQueryProcessor, HybridRetriever, is_enabled, load_tsu_by_id
from core.retrieval import ParsedQuery, QueryParser, ResponsePackage

_parser = QueryParser()

FIXTURE_TSUS = [
    {
        "tsu_id": "TSU-ROM-001",
        "content": "바울은 하나님의 은혜 곧 값없는 선물에 대해 가르친다",
        "title": "로마서 주석",
        "author": "칼빈",
        "source_file": "romans_commentary.pdf",
        "verse_mapping": {"book_id": "ROM"},
        "language": "ko",
    },
    {
        "tsu_id": "TSU-ACT-001",
        "content": "사도행전은 초대교회에 임한 은혜 곧 성장을 기록한다",
        "title": "사도행전 주석",
        "author": "라이트",
        "source_file": "acts_commentary.pdf",
        "verse_mapping": {"book_id": "ACT"},
        "language": "ko",
    },
]


@pytest.fixture()
def dataset_path(tmp_path):
    path = tmp_path / "tsu_dataset.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for tsu in FIXTURE_TSUS:
            f.write(json.dumps(tsu, ensure_ascii=False) + "\n")
    return path


@pytest.fixture()
def retriever(tmp_path, dataset_path):
    index_dir = tmp_path / "tantivy_index"
    build_index(dataset_path, index_dir)
    generator = CandidateGenerator(index_dir)
    tsu_by_id = load_tsu_by_id(str(dataset_path))
    return HybridRetriever(generator, tsu_by_id)


def _pq(query: str) -> ParsedQuery:
    return ParsedQuery(original_query=query, intent="unknown")


QUERY_PLANNER_FIXTURE_TSUS = [
    {
        "tsu_id": "TSU-ROM-828",
        "content": "이 구절은 모든 것이 합력하여 선을 이룬다는 내용과는 무관한 다른 이야기를 다룬다",
        "title": "무관한 문서",
        "author": "무명",
        "source_file": "unrelated.pdf",
        "verse_mapping": {"book_id": "ROM", "chapter": 8, "verse_start": 28},
        "language": "ko",
    },
    {
        "tsu_id": "TSU-EXACT-INORDER",
        # NOTE: keeps "하나님의 나라" as two standalone space-separated
        # tokens (matching the exact_phrase query) — Tantivy's default
        # tokenizer has no Korean morphology, so a particle-attached form
        # like "나라는" would NOT match a phrase query for "나라" (same
        # issue documented in tests/test_candidate_generator.py).
        "content": "하나님의 나라 복음을 전파하라",
        "title": "설교",
        "author": "무명",
        "source_file": "sermon.pdf",
        "verse_mapping": {},
        "language": "ko",
    },
    {
        "tsu_id": "TSU-EXACT-SCRAMBLED",
        "content": "나라 하나님의 통치 아래 있다",
        "title": "설교2",
        "author": "무명",
        "source_file": "sermon2.pdf",
        "verse_mapping": {},
        "language": "ko",
    },
    {
        "tsu_id": "TSU-METADATA-TITLE",
        "content": "이 문서의 본문에는 저자 이름이 전혀 등장하지 않는다",
        # NOTE: "Calvin" kept standalone (space before "연구") — a
        # code-switched attached form like "Calvin에" would tokenize as one
        # token and not match a bare "Calvin" query.
        "title": "Calvin 연구",
        "author": "다른저자",
        "source_file": "calvin_study.pdf",
        "verse_mapping": {},
        "language": "ko",
    },
]


@pytest.fixture()
def planner_dataset_path(tmp_path):
    path = tmp_path / "tsu_dataset.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for tsu in QUERY_PLANNER_FIXTURE_TSUS:
            f.write(json.dumps(tsu, ensure_ascii=False) + "\n")
    return path


@pytest.fixture()
def planner_retriever(tmp_path, planner_dataset_path):
    index_dir = tmp_path / "tantivy_index"
    build_index(planner_dataset_path, index_dir)
    generator = CandidateGenerator(index_dir)
    tsu_by_id = load_tsu_by_id(str(planner_dataset_path))

    bible_index_path = tmp_path / "bible_index.sqlite3"
    bible_index = BibleIndex(bible_index_path)
    bible_index.add_tsus(QUERY_PLANNER_FIXTURE_TSUS)

    return HybridRetriever(generator, tsu_by_id, bible_index=bible_index)


class TestQueryPlannerRouting:
    """[DBMA-SEARCH-INFRA-001 Query Planner] Verifies the routes actually
    change HybridRetriever's behavior, not just that classify() returns the
    right label in isolation."""

    def test_bible_route_finds_match_with_no_shared_keywords(self, planner_retriever):
        # TSU-ROM-828's content shares NO words with "롬 8:28" — a free-text
        # BM25 search would never surface it. Only the Bible Index (exact
        # verse_mapping match) can find it.
        parsed = _parser.parse("롬 8:28")
        results = planner_retriever.retrieve(parsed, k_output=10)
        ids = {r.tsu_id for r in results}
        assert "TSU-ROM-828" in ids

    def test_bible_route_handles_colon_syntax_that_breaks_tantivy(self, planner_retriever):
        # "Romans 5:1-10"-style strings raise ValueError if sent straight
        # into Tantivy's query parser (Phase 2-6 finding) — must not crash.
        parsed = _parser.parse("Romans 8:28")
        results = planner_retriever.retrieve(parsed, k_output=10)
        assert isinstance(results, list)  # no exception

    def test_exact_route_respects_word_order(self, planner_retriever):
        parsed = _parser.parse('"하나님의 나라"')
        results = planner_retriever.retrieve(parsed, k_output=10)
        ids = {r.tsu_id for r in results}
        assert "TSU-EXACT-INORDER" in ids
        assert "TSU-EXACT-SCRAMBLED" not in ids

    def test_metadata_route_matches_title_even_when_absent_from_content(self, planner_retriever):
        parsed = _parser.parse("Calvin")
        results = planner_retriever.retrieve(parsed, k_output=10)
        ids = {r.tsu_id for r in results}
        assert "TSU-METADATA-TITLE" in ids


class TestHybridRetriever:
    def test_returns_ranked_candidates_with_metadata(self, retriever):
        results = retriever.retrieve(_pq("은혜"), k_output=10)
        assert results
        ids = {r.tsu_id for r in results}
        assert ids == {"TSU-ROM-001", "TSU-ACT-001"}
        for r in results:
            assert r.metadata.get("verse_mapping", {}).get("book_id") in {"ROM", "ACT"}

    def test_k_output_caps_results(self, retriever):
        results = retriever.retrieve(_pq("은혜"), k_output=1)
        assert len(results) == 1

    def test_no_match_returns_empty(self, retriever):
        results = retriever.retrieve(_pq("asdkfjqpwiuxcvz"), k_output=10)
        assert results == []

    def test_results_sorted_by_final_score_descending(self, retriever):
        results = retriever.retrieve(_pq("은혜"), k_output=10)
        scores = [r.final_score for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_missing_tsu_in_lookup_is_skipped_not_erroring(self, tmp_path, dataset_path):
        index_dir = tmp_path / "idx2"
        build_index(dataset_path, index_dir)
        generator = CandidateGenerator(index_dir)
        retriever = HybridRetriever(generator, tsu_by_id={})  # empty lookup dict
        results = retriever.retrieve(_pq("은혜"), k_output=10)
        assert results == []


class TestLoadTsuById:
    def test_loads_by_tsu_id(self, dataset_path):
        tsu_by_id = load_tsu_by_id(str(dataset_path))
        assert set(tsu_by_id.keys()) == {"TSU-ROM-001", "TSU-ACT-001"}
        assert tsu_by_id["TSU-ROM-001"]["title"] == "로마서 주석"


class TestHybridRetrieverTelemetryOut:
    def test_telemetry_out_populated_for_hybrid_route(self, retriever):
        telemetry_out = {}
        retriever.retrieve(_pq("은혜"), k_output=10, telemetry_out=telemetry_out)
        assert telemetry_out["route"] == "hybrid"
        assert telemetry_out["candidate_count"] > 0
        assert telemetry_out["merge_time_ms"] >= 0.0

    def test_telemetry_out_none_does_not_error(self, retriever):
        results = retriever.retrieve(_pq("은혜"), k_output=10, telemetry_out=None)
        assert results  # no exception, default behavior unaffected


class TestHybridRetrieverFileScope:
    def test_file_scope_restricts_to_named_source_files(self, retriever):
        results = retriever.retrieve(_pq("은혜"), k_output=10, file_scope=["acts_commentary.pdf"])
        ids = {r.tsu_id for r in results}
        assert ids == {"TSU-ACT-001"}

    def test_file_scope_none_searches_everything(self, retriever):
        results = retriever.retrieve(_pq("은혜"), k_output=10, file_scope=None)
        ids = {r.tsu_id for r in results}
        assert ids == {"TSU-ROM-001", "TSU-ACT-001"}


class TestHybridQueryProcessor:
    """[DBMA-SEARCH-INFRA-001 Phase 2-6] Drop-in replacement for
    core.retrieval.QueryProcessor's .process() interface."""

    @pytest.fixture()
    def processor(self, tmp_path, dataset_path):
        index_dir = tmp_path / "tantivy_index"
        bible_index_path = tmp_path / "bible_index.sqlite3"
        telemetry_path = tmp_path / "search_telemetry.sqlite3"
        cache_path = tmp_path / "search_cache.sqlite3"
        manifest_path = tmp_path / "tsu_manifest.json"  # deliberately absent -> fingerprint=None
        return HybridQueryProcessor(
            tsu_dataset_path=str(dataset_path),
            candidate_index_dir=str(index_dir),
            bible_index_path=str(bible_index_path),
            telemetry_path=str(telemetry_path),
            cache_path=str(cache_path),
            tsu_manifest_path=str(manifest_path),
        )

    def test_process_returns_response_package(self, processor):
        response = processor.process("은혜", query_id="q1", k=10)
        assert isinstance(response, ResponsePackage)
        assert response.query_id == "q1"
        assert response.question == "은혜"
        ids = {c.tsu_id for c in response.top_k_results}
        assert ids == {"TSU-ROM-001", "TSU-ACT-001"}

    def test_process_populates_citations_and_context(self, processor):
        response = processor.process("은혜", k=10)
        assert response.citations
        assert response.llm_context_block

    def test_process_respects_k(self, processor):
        response = processor.process("은혜", k=1)
        assert len(response.top_k_results) == 1

    def test_process_records_total_ms(self, processor):
        response = processor.process("은혜", k=10)
        assert response.performance_metrics.total_ms >= 0

    def test_process_no_match_returns_empty_results(self, processor):
        response = processor.process("asdkfjqpwiuxcvz", k=10)
        assert response.top_k_results == []

    def test_process_respects_file_scope(self, processor):
        response = processor.process("은혜", k=10, file_scope=["acts_commentary.pdf"])
        ids = {c.tsu_id for c in response.top_k_results}
        assert ids == {"TSU-ACT-001"}

    # --- [DBMA-SEARCH-INFRA-001 HQ 제안 ⑨] Search Telemetry wiring ---
    # process() must record telemetry for every call and expose a
    # correlation id for click tracking.

    def test_process_sets_telemetry_query_id(self, processor):
        response = processor.process("은혜", k=10)
        assert isinstance(response.telemetry_query_id, int)

    def test_process_records_a_query_row(self, processor):
        processor.process("은혜", k=10)
        assert processor.telemetry.success_rate() == 1.0

    def test_zero_hit_query_recorded_as_zero_hit(self, processor):
        processor.process("asdkfjqpwiuxcvz", k=10)
        assert processor.telemetry.zero_hit_rate() == 1.0

    def test_click_can_be_recorded_against_returned_query_id(self, processor):
        response = processor.process("은혜", k=10)
        processor.telemetry.record_click(response.telemetry_query_id, tsu_id="TSU-ROM-001", rank=1)
        assert processor.telemetry.click_through_rate(top_n=1) == 1.0

    def test_candidate_count_and_merge_time_recorded(self, processor):
        processor.process("은혜", k=10)
        assert processor.telemetry.avg_candidate_count() > 0
        assert processor.telemetry.avg_merge_time_ms() >= 0.0

    def test_route_recorded_matches_query_planner(self, processor):
        processor.process("은혜", k=10)  # short, non-Latin — routes to hybrid
        import sqlite3
        conn = sqlite3.connect(processor.telemetry.db_path)
        route = conn.execute("SELECT route FROM search_query LIMIT 1").fetchone()[0]
        assert route == "hybrid"

    # --- [DBMA-SEARCH-INFRA-001 HQ 제안 ⑥] Search Result Cache wiring ---

    def test_second_identical_query_is_a_cache_hit(self, processor):
        processor.process("은혜", k=10)
        response2 = processor.process("은혜", k=10)
        import sqlite3
        conn = sqlite3.connect(processor.telemetry.db_path)
        routes = [r[0] for r in conn.execute("SELECT route FROM search_query ORDER BY id").fetchall()]
        assert routes == ["hybrid", "cache"]
        assert processor.telemetry.cache_hit_rate() == pytest.approx(0.5)

    def test_cache_hit_returns_same_results_as_miss(self, processor):
        response1 = processor.process("은혜", k=10)
        response2 = processor.process("은혜", k=10)
        ids1 = [c.tsu_id for c in response1.top_k_results]
        ids2 = [c.tsu_id for c in response2.top_k_results]
        assert ids1 == ids2

    def test_different_k_is_not_a_cache_hit(self, processor):
        processor.process("은혜", k=10)
        processor.process("은혜", k=5)
        assert processor.telemetry.cache_hit_rate() == 0.0

    def test_different_file_scope_is_not_a_cache_hit(self, processor):
        processor.process("은혜", k=10)
        processor.process("은혜", k=10, file_scope=["acts_commentary.pdf"])
        assert processor.telemetry.cache_hit_rate() == 0.0


class TestFeatureFlag:
    def test_disabled_by_default(self, monkeypatch):
        monkeypatch.delenv("USE_INVERTED_INDEX", raising=False)
        assert is_enabled() is False

    def test_enabled_when_true(self, monkeypatch):
        monkeypatch.setenv("USE_INVERTED_INDEX", "true")
        assert is_enabled() is True

    def test_case_insensitive(self, monkeypatch):
        monkeypatch.setenv("USE_INVERTED_INDEX", "TRUE")
        assert is_enabled() is True

    def test_other_values_are_disabled(self, monkeypatch):
        monkeypatch.setenv("USE_INVERTED_INDEX", "1")
        assert is_enabled() is False
