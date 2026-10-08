"""[2026-09-26] Book-name queries returned 0 results on a corpus where every
TSU's document-level book_id is "UNK" (sermon collections, not single-book
commentaries) — see docs/NAE_BOOK_ID_FILTER_ZERO_RESULT_INVESTIGATION_001.md.

Fixture mirrors the real corpus shape: verse_mapping == {} everywhere, so the
Tantivy book_id field is empty and the Bible Index has zero postings."""

import json

import pytest

from core.bible_index import BibleIndex
from core.candidate_generator import CandidateGenerator, build_index
from core.hybrid_candidate_pipeline import HybridRetriever, load_tsu_by_id
from core.retrieval import QueryParser

UNK_TSUS = [
    {
        "tsu_id": "TSU-UNK-a_chunk_00001",
        "content": "Romans teaches justification by faith alone, apart from works",
        "title": "Sermons Vol 1",
        "author": "Spurgeon",
        "source_file": "spurgeon_vol1.txt",
        "verse_mapping": {},
        "language": "en",
    },
    {
        "tsu_id": "TSU-UNK-b_chunk_00001",
        "content": "All things work together for good to them that love God",
        "title": "Sermons Vol 2",
        "author": "Spurgeon",
        "source_file": "spurgeon_vol2.txt",
        "verse_mapping": {},
        "language": "en",
    },
    {
        "tsu_id": "TSU-UNK-c_chunk_00001",
        "content": "The history of preaching among the early fathers",
        "title": "Lectures",
        "author": "Broadus",
        "source_file": "broadus.txt",
        "verse_mapping": {},
        "language": "en",
    },
]

_parser = QueryParser()


@pytest.fixture()
def unk_retriever(tmp_path):
    dataset = tmp_path / "tsu_dataset.jsonl"
    with open(dataset, "w", encoding="utf-8") as f:
        for tsu in UNK_TSUS:
            f.write(json.dumps(tsu, ensure_ascii=False) + "\n")
    index_dir = tmp_path / "tantivy_index"
    build_index(dataset, index_dir)
    bible_index = BibleIndex(tmp_path / "bible_index.sqlite3")
    bible_index.add_tsus(UNK_TSUS)  # all verse_mapping empty -> 0 postings
    return HybridRetriever(
        CandidateGenerator(index_dir), load_tsu_by_id(str(dataset)), bible_index=bible_index
    )


class TestAutoBookFilterFallback:
    def test_english_book_query_finds_unk_text(self, unk_retriever):
        parsed = _parser.parse("Romans justification by faith")
        assert parsed.detected_books == ["ROM"]
        ids = [r.tsu_id for r in unk_retriever.retrieve(parsed, k_output=5)]
        assert ids and ids[0] == "TSU-UNK-a_chunk_00001"

    def test_korean_book_query_finds_unk_text_via_translation(self, unk_retriever):
        parsed = _parser.parse("로마서의 이신칭의")
        ids = [r.tsu_id for r in unk_retriever.retrieve(parsed, k_output=5)]
        assert "TSU-UNK-a_chunk_00001" in ids

    def test_fallback_keeps_user_file_scope(self, unk_retriever):
        parsed = _parser.parse("Romans justification by faith")
        results = unk_retriever.retrieve(parsed, k_output=5, file_scope=["broadus.txt"])
        assert {r.metadata["source_file"] for r in results} <= {"broadus.txt"}

    def test_explicit_book_ids_are_not_dropped(self, unk_retriever):
        # Only the parser-derived filter falls back; a caller's explicit
        # book_ids stays a hard constraint.
        parsed = _parser.parse("Romans justification by faith")
        hits = unk_retriever.candidate_generator.search(parsed, k=5, book_ids=["ROM"])
        assert hits == []


class TestBibleRouteEmptyIndexFallback:
    def test_verse_query_falls_back_to_text_search(self, unk_retriever):
        parsed = _parser.parse("Romans 8:28 all things work together for good")
        telemetry: dict = {}
        results = unk_retriever.retrieve(parsed, k_output=5, telemetry_out=telemetry)
        assert telemetry["route"] == "hybrid"
        assert telemetry["route_fallback_from"] == "bible"
        assert "TSU-UNK-b_chunk_00001" in {r.tsu_id for r in results}
