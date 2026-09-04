"""Tests for core/bible_index.py (DBMA-SEARCH-INFRA-001 Phase 2-3)."""

import json

import pytest

from core.bible_index import (
    BibleIndex,
    build_index,
    canonical_key,
    keys_for_scripture_ref,
    resolve_query,
)
from core.retrieval import QueryParser, ScriptureReference


class TestCanonicalKey:
    def test_book_only(self):
        assert canonical_key("ROM") == "Bible.Romans"

    def test_book_and_chapter(self):
        assert canonical_key("ROM", 8) == "Bible.Romans.8"

    def test_book_chapter_verse(self):
        assert canonical_key("ROM", 8, 28) == "Bible.Romans.8.28"

    def test_unknown_book_id_falls_back_to_raw_id(self):
        assert canonical_key("ZZZ") == "Bible.ZZZ"


class TestNormalizationReuse:
    """The whole point of Phase 2-3: '롬 8:28', '롬8:28', and 'Romans 8:28'
    must all resolve to the identical canonical key, via the EXISTING
    QueryParser — not a new parser written for this module."""

    @pytest.mark.parametrize("query", ["Romans 8:28", "롬 8:28", "롬8:28", "rom 8:28"])
    def test_variant_forms_produce_same_canonical_key(self, query):
        parsed = QueryParser().parse(query)
        assert len(parsed.scripture_refs) == 1
        ref = parsed.scripture_refs[0]
        keys = keys_for_scripture_ref(ref)
        assert "Bible.Romans.8.28" in keys


class TestBibleIndexPostings:
    @pytest.fixture()
    def index(self, tmp_path):
        return BibleIndex(tmp_path / "bible_index.sqlite3")

    def test_verse_level_tsu_indexed_at_all_granularities(self, index):
        tsu = {
            "tsu_id": "TSU-ROM-001",
            "document_id": "DOC-1",
            "verse_mapping": {"book_id": "ROM", "chapter": 8, "verse_start": 28},
        }
        n = index.add_tsus([tsu])
        assert n == 3  # book + chapter + verse
        assert index.lookup("Bible.Romans") == ["TSU-ROM-001"]
        assert index.lookup("Bible.Romans.8") == ["TSU-ROM-001"]
        assert index.lookup("Bible.Romans.8.28") == ["TSU-ROM-001"]

    def test_verse_range_indexed_per_verse(self, index):
        tsu = {
            "tsu_id": "TSU-ROM-002",
            "document_id": "DOC-1",
            "verse_mapping": {"book_id": "ROM", "chapter": 8, "verse_start": 28, "verse_end": 30},
        }
        index.add_tsus([tsu])
        assert index.lookup("Bible.Romans.8.28") == ["TSU-ROM-002"]
        assert index.lookup("Bible.Romans.8.29") == ["TSU-ROM-002"]
        assert index.lookup("Bible.Romans.8.30") == ["TSU-ROM-002"]
        assert index.lookup("Bible.Romans.8.31") == []

    def test_book_only_tsu_indexed_at_book_level_only(self, index):
        tsu = {"tsu_id": "TSU-ACT-001", "document_id": "DOC-2", "verse_mapping": {"book_id": "ACT"}}
        n = index.add_tsus([tsu])
        assert n == 1
        assert index.lookup("Bible.Acts") == ["TSU-ACT-001"]
        assert index.lookup("Bible.Acts.1") == []

    def test_missing_verse_mapping_indexes_nothing(self, index):
        n = index.add_tsus([{"tsu_id": "TSU-X", "document_id": "DOC-3", "verse_mapping": {}}])
        assert n == 0

    def test_lookup_scripture_ref_falls_back_verse_to_chapter_to_book(self, index):
        # Only book-level evidence for this TSU (the common case, ~76% of corpus).
        index.add_tsus([{"tsu_id": "TSU-ROM-BOOK", "document_id": "DOC-1",
                          "verse_mapping": {"book_id": "ROM"}}])
        ref = ScriptureReference(book_id="ROM", chapter=8, verse_start=28)
        # No verse- or chapter-level rows exist, so this must fall back to the book key.
        assert index.lookup_scripture_ref(ref) == ["TSU-ROM-BOOK"]

    def test_lookup_scripture_ref_prefers_most_specific_match(self, index):
        index.add_tsus([
            {"tsu_id": "TSU-BOOK-ONLY", "document_id": "DOC-1", "verse_mapping": {"book_id": "ROM"}},
            {"tsu_id": "TSU-VERSE-EXACT", "document_id": "DOC-2",
             "verse_mapping": {"book_id": "ROM", "chapter": 8, "verse_start": 28}},
        ])
        ref = ScriptureReference(book_id="ROM", chapter=8, verse_start=28)
        assert index.lookup_scripture_ref(ref) == ["TSU-VERSE-EXACT"]


class TestReplaceAndDeleteDocument:
    @pytest.fixture()
    def index(self, tmp_path):
        return BibleIndex(tmp_path / "bible_index.sqlite3")

    def test_replace_document_swaps_postings(self, index):
        index.add_tsus([{"tsu_id": "TSU-OLD", "document_id": "DOC-1",
                          "verse_mapping": {"book_id": "ROM", "chapter": 8, "verse_start": 28}}])
        assert index.lookup("Bible.Romans.8.28") == ["TSU-OLD"]

        index.replace_document("DOC-1", [{"tsu_id": "TSU-NEW", "document_id": "DOC-1",
                                           "verse_mapping": {"book_id": "ROM", "chapter": 9, "verse_start": 1}}])
        assert index.lookup("Bible.Romans.8.28") == []
        assert index.lookup("Bible.Romans.9.1") == ["TSU-NEW"]

    def test_delete_document_removes_all_its_postings(self, index):
        index.add_tsus([
            {"tsu_id": "TSU-A", "document_id": "DOC-1", "verse_mapping": {"book_id": "ROM", "chapter": 8}},
            {"tsu_id": "TSU-B", "document_id": "DOC-2", "verse_mapping": {"book_id": "ROM", "chapter": 8}},
        ])
        index.delete_document("DOC-1")
        assert index.lookup("Bible.Romans.8") == ["TSU-B"]


class TestBuildIndexFromDataset:
    def test_builds_from_jsonl(self, tmp_path):
        dataset_path = tmp_path / "tsu_dataset.jsonl"
        records = [
            {"tsu_id": "TSU-1", "document_id": "DOC-1",
             "verse_mapping": {"book_id": "JHN", "chapter": 3, "verse_start": 16}},
            {"tsu_id": "TSU-2", "document_id": "DOC-2", "verse_mapping": {"book_id": "ACT"}},
        ]
        with open(dataset_path, "w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")

        db_path = tmp_path / "bible_index.sqlite3"
        total = build_index(dataset_path, db_path)
        assert total == 4  # TSU-1: book+chapter+verse (3), TSU-2: book (1)

        index = BibleIndex(db_path)
        assert index.lookup("Bible.John.3.16") == ["TSU-1"]
        assert index.lookup("Bible.Acts") == ["TSU-2"]


class TestResolveQuery:
    def test_resolves_korean_and_english_forms_to_same_result(self, tmp_path):
        dataset_path = tmp_path / "tsu_dataset.jsonl"
        record = {"tsu_id": "TSU-1", "document_id": "DOC-1",
                  "verse_mapping": {"book_id": "ROM", "chapter": 8, "verse_start": 28}}
        with open(dataset_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

        index = BibleIndex(tmp_path / "bible_index.sqlite3")
        index.add_tsus([record])

        assert resolve_query(index, "Romans 8:28") == ["TSU-1"]
        assert resolve_query(index, "롬 8:28") == ["TSU-1"]
        assert resolve_query(index, "롬8:28") == ["TSU-1"]

    def test_no_scripture_ref_returns_empty(self, tmp_path):
        index = BibleIndex(tmp_path / "bible_index.sqlite3")
        assert resolve_query(index, "은혜에 대하여") == []
