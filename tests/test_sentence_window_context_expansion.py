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


# ── [J2, 2026-10-18] 완성된 문단 경계 정리 ──────────────────────
#
# ADR-034의 이어붙이기만으로는 블록 앞뒤가 문장 중간에서 시작·끝났고
# (프로덕션 청크의 31.1%가 중간 절단), chunk_overlap=120 때문에 경계에서
# 같은 문장이 두 번 보였다. core/paragraph_context.py가 이웃의 깨진
# 앞머리·꼬리만 버리고 겹침을 한 번만 남긴다.
#
# 실측(코퍼스 119,595건 중 3,000 표본, 이웃 1개씩):
#   문장 종결률 69.1% → 99.5%,  문장 시작률 32.2% → 97.3%


def test_block_starts_and_ends_at_sentence_boundaries(tmp_path):
    records = _doc_records("doc1", [
        "ment of the covenant. The promise was given to Abraham.",
        "Justification is an act; sanctification is a work.",
        "The Spirit applies it daily. Then it breaks off mid-sen",
    ])
    engine = _make_engine(tmp_path, records)
    cand = _cand("doc1", "doc1_chunk_00001",
                 "Justification is an act; sanctification is a work.")

    block, _ = ContextAssembler().assemble(
        [cand],
        ParsedQuery(original_query="q", intent="unknown"),
        neighbor_lookup=engine.get_neighbor_context,
        num_neighbors=1,
    )

    body = block.split(">", 1)[1]  # <context …> 태그 다음부터
    assert "ment of the covenant." not in body      # 깨진 앞머리 제거
    assert "The promise was given to Abraham." in body
    assert "Then it breaks off mid-sen" not in body  # 깨진 꼬리 제거
    assert "The Spirit applies it daily." in body


def test_matched_chunk_body_is_never_trimmed(tmp_path):
    """검색이 찾아낸 근거는 한 글자도 깎지 않는다 — 깎으면 근거가 줄어든다."""
    matched = "mid-sentence start of the matched chunk and it ends mid-sent"
    records = _doc_records("doc1", ["Head sentence. broken", matched, "broken tail"])
    engine = _make_engine(tmp_path, records)
    cand = _cand("doc1", "doc1_chunk_00001", matched)

    block, _ = ContextAssembler().assemble(
        [cand],
        ParsedQuery(original_query="q", intent="unknown"),
        neighbor_lookup=engine.get_neighbor_context,
        num_neighbors=1,
    )
    assert matched in block


def test_overlap_between_neighbours_appears_once(tmp_path):
    """chunk_overlap의 산물 — 같은 문장이 블록에 두 번 보이면 안 된다."""
    shared = "This sentence lies in the overlap region of both chunks."
    records = _doc_records("doc1", [
        "Opening sentence. " + shared,
        shared + " The matched chunk continues from there.",
    ])
    engine = _make_engine(tmp_path, records)
    cand = _cand("doc1", "doc1_chunk_00001",
                 shared + " The matched chunk continues from there.")

    block, _ = ContextAssembler().assemble(
        [cand],
        ParsedQuery(original_query="q", intent="unknown"),
        neighbor_lookup=engine.get_neighbor_context,
        num_neighbors=1,
    )
    assert block.count(shared) == 1


def test_candidates_are_not_mutated_by_assembly(tmp_path):
    """ADR-034 불변식 — 랭킹·스코어·citation 산출에 영향이 없어야 한다.
    조립은 블록 문자열만 만들고 후보 객체는 건드리지 않는다."""
    records = _doc_records("doc1", ["Head. one", "two", "three tail"])
    engine = _make_engine(tmp_path, records)
    cand = _cand("doc1", "doc1_chunk_00001", "two")
    before_content, before_score, before_meta = cand.content, cand.final_score, dict(cand.metadata)

    ContextAssembler().assemble(
        [cand],
        ParsedQuery(original_query="q", intent="unknown"),
        neighbor_lookup=engine.get_neighbor_context,
        num_neighbors=1,
    )

    assert cand.content == before_content
    assert cand.final_score == before_score
    assert cand.metadata == before_meta


def test_scripture_context_still_uses_the_matched_chunk_only(tmp_path):
    """scripture_contexts는 확장 전 본문 기준이어야 한다(ADR-034 경계)."""
    records = _doc_records("doc1", ["Head. before text", "matched text", "after text"])
    engine = _make_engine(tmp_path, records)
    cand = _cand("doc1", "doc1_chunk_00001", "matched text")

    _, scripture = ContextAssembler().assemble(
        [cand],
        ParsedQuery(original_query="q", intent="unknown"),
        neighbor_lookup=engine.get_neighbor_context,
        num_neighbors=1,
    )
    assert len(scripture) == 1
    assert "matched text" in scripture[0]
    assert "before text" not in scripture[0]
    assert "after text" not in scripture[0]


# ── [J2, 2026-10-18] 하이브리드 경로 배선 ───────────────────────
#
# 2026-09-18 USE_INVERTED_INDEX 기본 true 전환 이후 프로덕션 질의는
# HybridQueryProcessor를 타는데, 그 경로가 assemble()을 이웃 확장 인자 없이
# 호출해 Approved ADR-034가 사실상 비활성이었다. 실측(한국어 질의 4건
# 19블록): 종결률 52.6% → 배선 후 89.5%, 표본 확대(20질의 100블록) 98.0%.
#
# 이 테스트는 "두 경로가 같은 표면을 쓴다"는 것만 고정한다 — 엔진 전체를
# 띄우지 않고 _EngineCompat의 이웃 색인 표면만 검증한다(프로덕션 코퍼스
# 의존·GPU 의존 없이 회귀로 돌 수 있게).


def _tsu(document_id, idx, content):
    return {
        "tsu_id": f"TSU-X-{document_id}-{idx}",
        "document_id": document_id,
        "chunk_id": f"{document_id}_chunk_{idx:05d}",
        "content": content,
    }


def test_engine_compat_exposes_the_same_neighbor_surface():
    """_EngineCompat이 RetrievalEngine과 같은 메서드 이름·시그니처를 갖는다 —
    assemble(neighbor_lookup=...)에 그대로 넘길 수 있어야 한다."""
    from core.hybrid_candidate_pipeline import _EngineCompat

    records = {f"doc1_chunk_{i:05d}": _tsu("doc1", i, c)
               for i, c in enumerate(["첫 청크", "가운데 청크", "마지막 청크"])}
    compat = _EngineCompat(records)

    before, after = compat.get_neighbor_context(
        {"document_id": "doc1", "chunk_id": "doc1_chunk_00001"}, num_neighbors=1
    )
    assert [c for _, c in before] == ["첫 청크"]
    assert [c for _, c in after] == ["마지막 청크"]


def test_engine_compat_neighbor_matches_retrieval_engine(tmp_path):
    """같은 코퍼스에서 두 구현의 반환값이 동일해야 한다 — 로직을 복제하지
    않고 core/neighbor_index.py를 공유하므로 어긋날 수 없다는 것을 고정."""
    from core.hybrid_candidate_pipeline import _EngineCompat

    contents = ["a 첫", "b 가운데", "c 다음", "d 마지막"]
    engine = _make_engine(tmp_path, _doc_records("doc1", contents))
    compat = _EngineCompat({t["chunk_id"]: t for t in _doc_records("doc1", contents)})

    for i in range(len(contents)):
        meta = {"document_id": "doc1", "chunk_id": f"doc1_chunk_{i:05d}"}
        assert engine.get_neighbor_context(meta, 1) == compat.get_neighbor_context(meta, 1)


def test_hybrid_processor_passes_neighbor_lookup_to_assemble(monkeypatch):
    """배선 자체를 고정한다 — process()가 assemble()에 neighbor_lookup과
    num_neighbors를 넘기지 않으면 ADR-034가 다시 비활성이 된다."""
    import inspect

    from core import hybrid_candidate_pipeline as mod

    src = inspect.getsource(mod.HybridQueryProcessor.process)
    assert "neighbor_lookup=self.engine.get_neighbor_context" in src
    assert "num_neighbors=CONTEXT_WINDOW_NEIGHBORS" in src
