"""Tests for core/candidate_generator.py (DBMA-SEARCH-INFRA-001 Phase 2-2)."""

import json

import pytest

from core.candidate_generator import CandidateGenerator, build_index, open_or_build_index
from core.retrieval import ParsedQuery

# NOTE: Tantivy's default tokenizer splits on whitespace only — no Korean
# morphological analysis, so a particle-attached form ("은혜를") will NOT
# match a bare term query ("은혜"). Fixture content below keeps keywords
# space-separated (as real theological prose commonly does, e.g. "하나님의
# 은혜 언약" — confirmed against the actual 100k benchmark corpus) so these
# tests exercise CandidateGenerator's own logic rather than Korean NLP,
# which is a known limitation tracked for a later Phase 2 iteration.
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
        "tsu_id": "TSU-ROM-002",
        "content": "로마서 8장은 성령 안에서의 삶을 다룬다",
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
def generator(tmp_path, dataset_path):
    index_dir = tmp_path / "tantivy_index"
    count = build_index(dataset_path, index_dir)
    assert count == len(FIXTURE_TSUS)
    return CandidateGenerator(index_dir)


def _pq(query: str, detected_books=None) -> ParsedQuery:
    return ParsedQuery(original_query=query, intent="unknown", detected_books=detected_books or [])


class TestBuildIndex:
    def test_indexes_all_documents(self, tmp_path, dataset_path):
        index_dir = tmp_path / "idx"
        count = build_index(dataset_path, index_dir)
        assert count == 3

    def test_missing_dataset_file_builds_empty_index_not_crash(self, tmp_path):
        """[CI validate 실패 수정, 2026-09-18] tsu_dataset_path가 없으면
        빈 코퍼스로 취급한다 — core/retrieval.py::RetrievalEngine.
        _load_corpus()가 이미 문서화한 "파일 없음 = 정상 초기 상태"
        계약과 동일. USE_INVERTED_INDEX 기본값이 true가 된 뒤, 이 함수만
        FileNotFoundError로 죽어 실제 코퍼스가 없는 환경(CI의 AppTest
        기반 UI 테스트 등)을 깨뜨렸다."""
        missing = tmp_path / "no_such_tsu_dataset.jsonl"
        index_dir = tmp_path / "idx"
        count = build_index(missing, index_dir)
        assert count == 0
        # 크래시 없이 열 수 있는 정상 인덱스여야 한다.
        CandidateGenerator(index_dir)


class TestOpenOrBuildIndexStaleness:
    """[Bug tracked since C1-TASK-ORDER-050-REPORT.md §5 "영어 쿼리 결과
    없음": BM25 인덱스(~80,000 docs)가 현재 tsu_by_id(53,963 entries)와
    데이터가 안 맞아 결과가 필터링됨] open_or_build_index() only checks
    whether meta.json exists — never whether the on-disk index still
    matches the current dataset on disk. Once a dataset changes (grows,
    shrinks, or gets reprocessed) without the index_dir also being wiped,
    every future call silently keeps serving the stale index forever."""

    def test_stale_index_is_rebuilt_when_dataset_changes(self, tmp_path, dataset_path):
        index_dir = tmp_path / "tantivy_index"
        open_or_build_index(dataset_path, index_dir)  # builds from the 3-doc fixture

        # Dataset changes on disk (same path, new content) — index_dir/
        # meta.json from the old build is still sitting there untouched.
        new_tsus = FIXTURE_TSUS + [
            {
                "tsu_id": "TSU-NEW-001",
                "content": "새로 추가된 유일무이스핑크스단어 문서",
                "title": "새 문서",
                "author": "무명",
                "source_file": "new_doc.pdf",
                "verse_mapping": {},
                "language": "ko",
            },
        ]
        with open(dataset_path, "w", encoding="utf-8") as f:
            for tsu in new_tsus:
                f.write(json.dumps(tsu, ensure_ascii=False) + "\n")

        generator = open_or_build_index(dataset_path, index_dir)

        assert generator._index.searcher().num_docs == len(new_tsus)
        results = generator.search(_pq("유일무이스핑크스단어"), k=10)
        ids = {c.tsu_id for c in results}
        assert "TSU-NEW-001" in ids

    def test_bootstrap_with_missing_dataset_file_does_not_crash(self, tmp_path):
        """[CI validate 실패 수정, 2026-09-18] 코퍼스 파일이 아직 없는
        첫 실행(예: CI, 초기화 직후)에서도 크래시 없이 빈 인덱스를
        연다 — meta_file이 없는 최초 부트스트랩 경로와, meta_file은
        있지만 데이터셋 파일이 그새 사라진 staleness 재확인 경로
        둘 다 커버한다."""
        missing = tmp_path / "no_such_tsu_dataset.jsonl"
        index_dir = tmp_path / "tantivy_index"

        generator = open_or_build_index(missing, index_dir)
        assert generator._index.searcher().num_docs == 0

        # 두 번째 호출(staleness 재확인 경로)도 여전히 파일이 없는 상태 —
        # 재빌드를 시도하다 크래시하지 않고 그대로 열려야 한다.
        generator_again = open_or_build_index(missing, index_dir)
        assert generator_again._index.searcher().num_docs == 0

    def test_matching_index_is_not_rebuilt_unnecessarily(self, tmp_path, dataset_path):
        # Perf guard: at real corpus scale a rebuild costs 60~200+ seconds
        # (C1-TASK-ORDER-033-REPORT.md §2 — Tantivy 100k=61.87s, 300k=195.37s).
        # A staleness fix that rebuilds on every open_or_build_index() call
        # regardless of whether anything changed would be a correctness fix
        # that silently reintroduces a much worse performance regression.
        index_dir = tmp_path / "tantivy_index"
        open_or_build_index(dataset_path, index_dir)
        mtime_before = (index_dir / "meta.json").stat().st_mtime

        open_or_build_index(dataset_path, index_dir)  # dataset unchanged
        mtime_after = (index_dir / "meta.json").stat().st_mtime

        assert mtime_after == mtime_before


class TestSearch:
    def test_keyword_match_returns_candidates(self, generator):
        results = generator.search(_pq("은혜"), k=10)
        ids = {c.tsu_id for c in results}
        assert ids == {"TSU-ROM-001", "TSU-ACT-001"}

    def test_no_match_returns_empty(self, generator):
        results = generator.search(_pq("asdkfjqpwiuxcvz"), k=10)
        assert results == []

    def test_k_caps_result_count(self, generator):
        results = generator.search(_pq("주석 로마서 사도행전 은혜 성령"), k=1)
        assert len(results) <= 1

    def test_book_filter_narrows_pool(self, generator):
        results = generator.search(_pq("은혜"), k=10, book_ids=["ACT"])
        ids = {c.tsu_id for c in results}
        assert ids == {"TSU-ACT-001"}

    def test_book_filter_from_parsed_query_detected_books(self, generator):
        results = generator.search(_pq("은혜", detected_books=["ROM"]), k=10)
        ids = {c.tsu_id for c in results}
        assert ids == {"TSU-ROM-001"}

    def test_source_file_filter(self, generator):
        results = generator.search(_pq("은혜"), k=10, source_files=["acts_commentary.pdf"])
        ids = {c.tsu_id for c in results}
        assert ids == {"TSU-ACT-001"}

    def test_candidate_ref_has_no_content_field(self, generator):
        results = generator.search(_pq("은혜"), k=10)
        assert results
        for c in results:
            assert not hasattr(c, "content")
            d = c.to_dict()
            assert "content" not in d

    def test_empty_query_returns_empty(self, generator):
        results = generator.search(_pq("   "), k=10)
        assert results == []

    def test_book_filter_falls_back_when_text_matches_nothing_in_that_book(self, generator):
        # "Compare" query (English-only tokens) filtered to ROM, but ROM's
        # fixture content is entirely Korean — a genuine empty intersection.
        # Should still return ROM candidates (metadata-filter-only fallback)
        # rather than dead-ending at zero results.
        results = generator.search(_pq("totally unrelated english words"), k=10, book_ids=["ROM"])
        ids = {c.tsu_id for c in results}
        assert ids == {"TSU-ROM-001", "TSU-ROM-002"}

    def test_parenthetical_query_does_not_raise(self, generator):
        """[2026-09-18 회귀] 괄호가 든 자연어 질의("중생(거듭남)은...")가
        Tantivy 쿼리 파서 문법 오류(ValueError)로 크래시하던 실사고 재현.
        USE_INVERTED_INDEX 기본 활성화 후 AT-5 실행 중 발견 —
        parse_query()가 소괄호를 그룹핑 문법으로 해석해 예외를 던졌다."""
        results = generator.search(_pq("은혜(값없는 선물)에 대해"), k=10)
        ids = {c.tsu_id for c in results}
        assert "TSU-ROM-001" in ids

    def test_other_tantivy_special_chars_do_not_raise(self, generator):
        for q in ['은혜: 정의', '은혜"강조"', '은혜 AND 성령', '은혜^2', '은혜~']:
            generator.search(_pq(q), k=10)  # 예외만 안 나면 통과

    def test_ascii_apostrophe_query_does_not_raise(self, generator):
        """[2026-09-18 회귀, P0-5 실채점 중 발견] "believer's baptism"처럼
        ASCII 아포스트로피가 든 영어 낱말이 섞인 질의(한영 자료 기반
        F유형)가 parse_query()에서 Syntax Error로 크래시하던 실사고
        재현 — 소괄호 수정 때는 잡히지 않았던 별도의 특수문자."""
        generator.search(_pq("믿음(believer's baptism)에 대해"), k=10)


class TestSnippets:
    """[DBMA-SEARCH-INFRA-001 Phase 2-5] Snippets generated via Tantivy's own
    SnippetGenerator for the k candidates returned — no separate preview
    fields stored at index time, no re-reading the source document."""

    def test_snippet_contains_matched_term(self, generator):
        results = generator.search(_pq("은혜"), k=10)
        assert results
        for c in results:
            assert c.snippet
            assert "은혜" in c.snippet

    def test_highlight_ranges_point_at_the_match(self, generator):
        results = generator.search(_pq("은혜"), k=10)
        assert results
        for c in results:
            assert c.highlight_ranges
            for start, end in c.highlight_ranges:
                assert c.snippet[start:end] == "은혜"

    def test_snippet_respects_max_chars(self, generator):
        results = generator.search(_pq("은혜"), k=10, snippet_max_chars=10)
        assert results
        for c in results:
            assert len(c.snippet) <= 10

    def test_with_snippets_false_skips_generation(self, generator):
        results = generator.search(_pq("은혜"), k=10, with_snippets=False)
        assert results
        for c in results:
            assert c.snippet == ""
            assert c.highlight_ranges == []

    def test_snippet_serializes_in_to_dict(self, generator):
        results = generator.search(_pq("은혜"), k=10)
        d = results[0].to_dict()
        assert d["snippet"] == results[0].snippet
        assert d["highlight_ranges"] == [list(r) for r in results[0].highlight_ranges]


class TestReindexDocument:
    def test_incremental_add_is_searchable(self, generator):
        assert generator.search(_pq("칭의"), k=10) == []

        new_tsu = {
            "tsu_id": "TSU-ROM-003",
            "content": "이신 칭의 교리는 믿음으로 의롭다 함을 받는 것을 뜻한다",
            "title": "로마서 주석",
            "author": "칼빈",
            "source_file": "romans_commentary.pdf",
            "verse_mapping": {"book_id": "ROM"},
            "language": "ko",
        }
        n = generator.reindex_document([new_tsu])
        assert n == 1

        results = generator.search(_pq("칭의"), k=10)
        ids = {c.tsu_id for c in results}
        assert "TSU-ROM-003" in ids

    def test_reindex_replaces_existing_tsu(self, generator):
        updated = dict(FIXTURE_TSUS[0])
        updated["content"] = "완전히 새로운 내용으로 교체됨 고유단어테스트"
        generator.reindex_document([updated])

        results = generator.search(_pq("고유단어테스트"), k=10)
        ids = {c.tsu_id for c in results}
        assert "TSU-ROM-001" in ids
