"""Regression test — ADR-034 Sentence-Window Context Expansion.

RetrievalEngine.get_neighbor_context()/ContextAssembler.assemble()의 이웃 청크
이어붙이기가 (a) 문서 경계/미인식 chunk에서 조용히 비어있는 리스트를 반환하고,
(b) LLM 컨텍스트 블록에만 영향을 주며 랭킹/스코어링/citation 대상인
RankedCandidate.content/metadata 자체는 절대 건드리지 않고, (c) 이미 top_k에
포함된 chunk는 이웃으로 중복 삽입하지 않는지 검증한다.
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.retrieval import ContextAssembler, ParsedQuery, RankedCandidate, RetrievalEngine


def _make_engine(tmp_path, records):
    dataset_path = tmp_path / "tsu_dataset.jsonl"
    with open(dataset_path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec) + "\n")
    return RetrievalEngine(tsu_dataset_path=dataset_path)


def _doc_records(document_id, contents):
    return [
        {
            "tsu_id": f"TSU-X-{document_id}-{idx}",
            "document_id": document_id,
            "chunk_id": f"{document_id}_chunk_{idx:05d}",
            "content": content,
        }
        for idx, content in enumerate(contents)
    ]


# ── RetrievalEngine.get_neighbor_context() ──────────────────────


def test_neighbor_context_middle_chunk_has_both_sides(tmp_path):
    records = _doc_records("doc1", ["첫 문단", "가운데 문단", "마지막 문단"])
    engine = _make_engine(tmp_path, records)

    before, after = engine.get_neighbor_context(
        {"document_id": "doc1", "chunk_id": "doc1_chunk_00001"}, num_neighbors=1
    )

    assert before == [("doc1_chunk_00000", "첫 문단")]
    assert after == [("doc1_chunk_00002", "마지막 문단")]


def test_neighbor_context_first_chunk_has_no_before(tmp_path):
    records = _doc_records("doc1", ["첫 문단", "가운데 문단", "마지막 문단"])
    engine = _make_engine(tmp_path, records)

    before, after = engine.get_neighbor_context(
        {"document_id": "doc1", "chunk_id": "doc1_chunk_00000"}, num_neighbors=1
    )

    assert before == []
    assert after == [("doc1_chunk_00001", "가운데 문단")]


def test_neighbor_context_last_chunk_has_no_after(tmp_path):
    records = _doc_records("doc1", ["첫 문단", "가운데 문단", "마지막 문단"])
    engine = _make_engine(tmp_path, records)

    before, after = engine.get_neighbor_context(
        {"document_id": "doc1", "chunk_id": "doc1_chunk_00002"}, num_neighbors=1
    )

    assert before == [("doc1_chunk_00001", "가운데 문단")]
    assert after == []


def test_neighbor_context_single_chunk_document_is_empty(tmp_path):
    records = _doc_records("doc1", ["유일한 문단"])
    engine = _make_engine(tmp_path, records)

    before, after = engine.get_neighbor_context(
        {"document_id": "doc1", "chunk_id": "doc1_chunk_00000"}, num_neighbors=1
    )

    assert before == []
    assert after == []


def test_neighbor_context_unknown_chunk_id_is_empty(tmp_path):
    records = _doc_records("doc1", ["첫 문단", "가운데 문단"])
    engine = _make_engine(tmp_path, records)

    before, after = engine.get_neighbor_context(
        {"document_id": "doc1", "chunk_id": "does-not-exist"}, num_neighbors=1
    )

    assert before == []
    assert after == []


def test_neighbor_context_missing_document_id_is_empty(tmp_path):
    records = _doc_records("doc1", ["첫 문단", "가운데 문단"])
    engine = _make_engine(tmp_path, records)

    before, after = engine.get_neighbor_context({"chunk_id": "doc1_chunk_00000"}, num_neighbors=1)

    assert before == []
    assert after == []


def test_neighbor_context_zero_neighbors_is_empty(tmp_path):
    records = _doc_records("doc1", ["첫 문단", "가운데 문단", "마지막 문단"])
    engine = _make_engine(tmp_path, records)

    before, after = engine.get_neighbor_context(
        {"document_id": "doc1", "chunk_id": "doc1_chunk_00001"}, num_neighbors=0
    )

    assert before == []
    assert after == []


def test_neighbor_context_cross_document_boundary_not_crossed(tmp_path):
    records = _doc_records("doc1", ["doc1 마지막"]) + _doc_records("doc2", ["doc2 첫 문단"])
    engine = _make_engine(tmp_path, records)

    before, after = engine.get_neighbor_context(
        {"document_id": "doc1", "chunk_id": "doc1_chunk_00000"}, num_neighbors=1
    )

    assert before == []
    assert after == []  # doc2 chunk는 다른 문서라 이웃이 아님


# ── ContextAssembler.assemble() 통합 ────────────────────────────


def _cand(document_id, chunk_id, content, score=0.5):
    return RankedCandidate(
        tsu_id=f"TSU-X-{chunk_id}",
        content=content,
        metadata={"document_id": document_id, "chunk_id": chunk_id},
        final_score=score,
    )


def test_assemble_without_neighbor_lookup_is_unchanged(tmp_path):
    cand = _cand("doc1", "doc1_chunk_00001", "가운데 문단")
    block, _ = ContextAssembler().assemble(
        [cand], ParsedQuery(original_query="q", intent="unknown")
    )
    assert "가운데 문단" in block
    assert block.count("문단") == 1


def test_assemble_with_neighbor_lookup_stitches_before_and_after(tmp_path):
    records = _doc_records("doc1", ["첫 문단", "가운데 문단", "마지막 문단"])
    engine = _make_engine(tmp_path, records)
    cand = _cand("doc1", "doc1_chunk_00001", "가운데 문단")

    block, _ = ContextAssembler().assemble(
        [cand],
        ParsedQuery(original_query="q", intent="unknown"),
        neighbor_lookup=engine.get_neighbor_context,
        num_neighbors=1,
    )

    assert "첫 문단" in block
    assert "가운데 문단" in block
    assert "마지막 문단" in block
    # 순서 보존: 이전 → 본문 → 이후
    assert block.index("첫 문단") < block.index("가운데 문단") < block.index("마지막 문단")


def test_assemble_does_not_duplicate_neighbor_already_in_top_k(tmp_path):
    records = _doc_records("doc1", ["첫 문단", "가운데 문단", "마지막 문단"])
    engine = _make_engine(tmp_path, records)
    # doc1_chunk_00000("첫 문단")과 doc1_chunk_00001("가운데 문단") 둘 다
    # 이미 top_k에 있으므로, 00001의 "이전 이웃"으로 "첫 문단"을 다시
    # 삽입하면 안 된다(중복 방지).
    cands = [
        _cand("doc1", "doc1_chunk_00000", "첫 문단"),
        _cand("doc1", "doc1_chunk_00001", "가운데 문단"),
    ]

    block, _ = ContextAssembler().assemble(
        cands,
        ParsedQuery(original_query="q", intent="unknown"),
        neighbor_lookup=engine.get_neighbor_context,
        num_neighbors=1,
    )

    assert block.count("첫 문단") == 1


def test_assemble_neighbor_expansion_does_not_affect_scores_or_metadata():
    """[ADR-034] 이웃 확장은 LLM 컨텍스트 블록 문자열에만 반영되고,
    RankedCandidate 자체(citation/랭킹의 원천)는 절대 변경되지 않는다."""
    cand = _cand("doc1", "doc1_chunk_00001", "가운데 문단", score=0.789)
    original_content = cand.content
    original_metadata = dict(cand.metadata)

    def fake_lookup(metadata, num_neighbors):
        return [("prev", "가짜 이전 문단")], [("next", "가짜 다음 문단")]

    ContextAssembler().assemble(
        [cand],
        ParsedQuery(original_query="q", intent="unknown"),
        neighbor_lookup=fake_lookup,
        num_neighbors=1,
    )

    assert cand.content == original_content
    assert cand.metadata == original_metadata
    assert cand.final_score == 0.789
