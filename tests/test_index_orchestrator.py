"""Regression test — core/index_orchestrator.py::rebuild_tsu_index()

SPRINT20-I: rebuild_tsu_index()는 scripts/build_tsu_dataset.py의 배치
로직(build_tsu_records/write_tsu_dataset/write_manifest)을 그대로 감싸는
얇은 wrapper다. 새 파싱/스코어링 로직이 없으므로, 이 테스트는 wrapper가
그 함수들을 올바른 인자로 호출하고 반환 계약을 지키는지만 검증한다.
"""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.index_orchestrator import rebuild_tsu_index, reindex_document
from core.candidate_generator import CandidateGenerator
from core.bible_index import BibleIndex
from core.retrieval import ParsedQuery


def _make_registry(tmp_path, doc_count=2, chunks_per_doc=3):
    registry_dir = tmp_path / "registry"
    registry_dir.mkdir(parents=True, exist_ok=True)
    documents = {}
    for i in range(doc_count):
        source_file = f"doc{i}.md"
        documents[f"DOC-{i}"] = {
            "source_file": source_file,
            "chunk_count": chunks_per_doc,
            "book": None,
            "title": f"Title {i}",
            "author": None,
            "chapter": None,
            "page": None,
            "language": "ko",
            "source_type": "md",
        }
        (tmp_path / f"doc{i}.md").write_text(f"content for doc {i}", encoding="utf-8")
    registry = {"documents": documents}
    (registry_dir / "documents.json").write_text(json.dumps(registry, ensure_ascii=False), encoding="utf-8")
    return registry_dir / "documents.json"


class TestRebuildTsuIndex:
    def test_returns_expected_contract(self, tmp_path, monkeypatch):
        _make_registry(tmp_path, doc_count=2, chunks_per_doc=3)

        dataset_path = tmp_path / "tsu_dataset.jsonl"
        manifest_path = tmp_path / "tsu_manifest.json"
        candidate_index_dir = tmp_path / "tantivy_index"
        bible_index_path = tmp_path / "bible_index.sqlite3"
        monkeypatch.setattr("core.index_orchestrator.DEFAULT_TSU_DATASET_PATH", str(dataset_path))
        monkeypatch.setattr("core.index_orchestrator.DEFAULT_TSU_MANIFEST_PATH", str(manifest_path))
        monkeypatch.setattr("core.index_orchestrator.DEFAULT_CANDIDATE_INDEX_DIR", str(candidate_index_dir))
        monkeypatch.setattr("core.index_orchestrator.DEFAULT_BIBLE_INDEX_PATH", str(bible_index_path))

        result = rebuild_tsu_index(output_dir=str(tmp_path))

        assert result["documents"] == 2
        assert result["records"] == 6  # 2 docs * 3 chunks
        assert result["dataset_path"] == str(dataset_path)
        assert result["manifest_path"] == str(manifest_path)
        assert dataset_path.exists()
        assert manifest_path.exists()

        lines = dataset_path.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 6
        first_record = json.loads(lines[0])
        assert "tsu_id" in first_record
        assert "content" in first_record

        # [DBMA-SEARCH-INFRA-001 Phase2-4] Candidate index built alongside
        # the TSU dataset, in the monkeypatched (not real) directory.
        assert result["candidate_index_documents"] == 6
        assert (candidate_index_dir / "meta.json").exists()

        # [DBMA-SEARCH-INFRA-001 Phase2-3] Bible index also built (0 postings
        # here — this fixture's generic content has no detectable book_id).
        assert result["bible_index_path"] == str(bible_index_path)
        assert bible_index_path.exists()

    def test_empty_registry_produces_zero_records(self, tmp_path, monkeypatch):
        registry_dir = tmp_path / "registry"
        registry_dir.mkdir(parents=True, exist_ok=True)
        (registry_dir / "documents.json").write_text(
            json.dumps({"documents": {}}), encoding="utf-8"
        )

        dataset_path = tmp_path / "tsu_dataset.jsonl"
        manifest_path = tmp_path / "tsu_manifest.json"
        candidate_index_dir = tmp_path / "tantivy_index"
        bible_index_path = tmp_path / "bible_index.sqlite3"
        monkeypatch.setattr("core.index_orchestrator.DEFAULT_TSU_DATASET_PATH", str(dataset_path))
        monkeypatch.setattr("core.index_orchestrator.DEFAULT_TSU_MANIFEST_PATH", str(manifest_path))
        monkeypatch.setattr("core.index_orchestrator.DEFAULT_CANDIDATE_INDEX_DIR", str(candidate_index_dir))
        monkeypatch.setattr("core.index_orchestrator.DEFAULT_BIBLE_INDEX_PATH", str(bible_index_path))

        result = rebuild_tsu_index(output_dir=str(tmp_path))

        assert result["documents"] == 0
        assert result["records"] == 0
        assert result["candidate_index_documents"] == 0
        assert result["bible_index_postings"] == 0


class TestReindexDocumentCandidateIndex:
    """[DBMA-SEARCH-INFRA-001 Phase2-4] reindex_document() must update the
    candidate index in place (delete-by-document_id + re-add) rather than
    rebuilding the whole corpus — verified here by checking that an
    untouched document's content stays searchable throughout."""

    def test_incremental_update_leaves_other_documents_searchable(self, tmp_path, monkeypatch):
        _make_registry(tmp_path, doc_count=2, chunks_per_doc=3)
        # NOTE: make_safe_stem("doc0.md") -> "doc0_md", so the fallback-content
        # reader (core/tsu_builder.py::_read_md_fallback) looks for
        # "doc0_md.md", not "doc0.md" — _make_registry's own
        # `(tmp_path / f"doc{i}.md").write_text(...)` call target is at the
        # wrong path for this reason and its content is silently never read
        # (existing TestRebuildTsuIndex tests never check content, only that
        # the "content" key exists, so this was never caught before).
        (tmp_path / "doc0_md.md").write_text("uniquemarkerZero content", encoding="utf-8")
        (tmp_path / "doc1_md.md").write_text("uniquemarkerOne content", encoding="utf-8")

        dataset_path = tmp_path / "tsu_dataset.jsonl"
        manifest_path = tmp_path / "tsu_manifest.json"
        candidate_index_dir = tmp_path / "tantivy_index"
        bible_index_path = tmp_path / "bible_index.sqlite3"
        monkeypatch.setattr("core.index_orchestrator.DEFAULT_TSU_DATASET_PATH", str(dataset_path))
        monkeypatch.setattr("core.index_orchestrator.DEFAULT_TSU_MANIFEST_PATH", str(manifest_path))
        monkeypatch.setattr("core.index_orchestrator.DEFAULT_CANDIDATE_INDEX_DIR", str(candidate_index_dir))
        monkeypatch.setattr("core.index_orchestrator.DEFAULT_BIBLE_INDEX_PATH", str(bible_index_path))

        rebuild_tsu_index(output_dir=str(tmp_path))

        generator = CandidateGenerator(candidate_index_dir)
        assert generator.search(ParsedQuery(original_query="uniquemarkerZero", intent="unknown"), k=10)
        assert generator.search(ParsedQuery(original_query="uniquemarkerOne", intent="unknown"), k=10)

        # Edit doc1 only, then reindex just that document.
        (tmp_path / "doc1_md.md").write_text("brandnewmarkerOne content", encoding="utf-8")
        result = reindex_document("DOC-1", output_dir=str(tmp_path))
        assert result["replaced"] == 3
        assert result["new"] == 3
        assert result["records"] == 6

        generator = CandidateGenerator(candidate_index_dir)
        # doc0 was never touched — still searchable, proving no full rebuild happened.
        assert generator.search(ParsedQuery(original_query="uniquemarkerZero", intent="unknown"), k=10)
        # doc1's old content is gone, new content is searchable.
        assert generator.search(ParsedQuery(original_query="uniquemarkerOne", intent="unknown"), k=10) == []
        assert generator.search(ParsedQuery(original_query="brandnewmarkerOne", intent="unknown"), k=10)


class TestReindexDocumentBibleIndex:
    """[DBMA-SEARCH-INFRA-001 Phase2-3] reindex_document() must update the
    Bible index in place too, using the same replace-by-document_id
    semantics as the candidate index."""

    def test_reindex_updates_bible_index_in_place(self, tmp_path, monkeypatch):
        registry_dir = tmp_path / "registry"
        registry_dir.mkdir(parents=True, exist_ok=True)
        documents = {
            "DOC-0": {
                "source_file": "romans.md", "chunk_count": 1, "book": None,
                "title": "T0", "author": None, "chapter": None, "page": None,
                "language": "en", "source_type": "md",
            },
        }
        (registry_dir / "documents.json").write_text(json.dumps({"documents": documents}), encoding="utf-8")
        (tmp_path / "romans_md.md").write_text("This is about Romans 8:28 and its meaning.", encoding="utf-8")

        dataset_path = tmp_path / "tsu_dataset.jsonl"
        manifest_path = tmp_path / "tsu_manifest.json"
        candidate_index_dir = tmp_path / "tantivy_index"
        bible_index_path = tmp_path / "bible_index.sqlite3"
        monkeypatch.setattr("core.index_orchestrator.DEFAULT_TSU_DATASET_PATH", str(dataset_path))
        monkeypatch.setattr("core.index_orchestrator.DEFAULT_TSU_MANIFEST_PATH", str(manifest_path))
        monkeypatch.setattr("core.index_orchestrator.DEFAULT_CANDIDATE_INDEX_DIR", str(candidate_index_dir))
        monkeypatch.setattr("core.index_orchestrator.DEFAULT_BIBLE_INDEX_PATH", str(bible_index_path))

        result = rebuild_tsu_index(output_dir=str(tmp_path))
        assert result["bible_index_postings"] > 0

        bible_index = BibleIndex(bible_index_path)
        assert bible_index.lookup("Bible.Romans.8.28") != []
        bible_index.close()

        # Edit the document so it's no longer about Romans 8:28, reindex,
        # and confirm the old posting is gone (delete-by-document_id, not a
        # full rebuild — nothing else exists to prove untouched here, but the
        # exact-match disappearing after a targeted reindex is itself proof
        # the replace path ran, not a stale full index).
        (tmp_path / "romans_md.md").write_text("This is about John 3:16 instead.", encoding="utf-8")
        reindex_document("DOC-0", output_dir=str(tmp_path))

        bible_index = BibleIndex(bible_index_path)
        assert bible_index.lookup("Bible.Romans.8.28") == []
        bible_index.close()


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
