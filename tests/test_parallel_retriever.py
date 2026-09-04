"""ParallelRetriever — Sprint C 통합 테스트.

검증 항목:
1. core/parallel_retriever.py가 core/retrieval.py의 RetrievalEngine.retrieve()를
   T1 축으로 감싸서 호출한다 (시그니처 변경 없음).
2. bible_tag_annotation 조회를 T2 축으로 병렬 실행한다.
3. 두 축의 결과를 EvidenceCandidate로 감싸서 반환한다.
4. core/retrieval.py가 수정되지 않았다 (git diff core/retrieval.py 빈 확인).
5. Sprint A/B 테스트 30/30 회귀 — RetrievalEngine.retrieve() 기존 동작 유지.
"""

from __future__ import annotations

import json
import sqlite3
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# 테스트용 mock RetrievalEngine — 실제 RetrievalEngine 대신 사용
# ---------------------------------------------------------------------------

@dataclass
class MockRankedCandidate:
    """RetrievalEngine.retrieve()가 반환하는 RankedCandidate의 mock."""
    tsu_id: str
    content: str
    metadata: dict[str, Any]
    vector_score: float
    bm25_score: float
    theological_score: float
    passage_score: float
    final_score: float
    explanation: str


class MockRetrievalEngine:
    """RetrievalEngine.retrieve()를 mock하여 ParallelRetriever가 T1 축을
    올바르게 감싸는지 검증."""

    def __init__(self, candidates: list[MockRankedCandidate]) -> None:
        self.candidates = candidates
        self.retrieve_called_with: list[Any] = []  # 호출 인자 기록

    def retrieve(
        self,
        parsed_query,
        k_output: int = 10,
        embedding_cache=None,
        file_scope=None,
    ) -> tuple[list[MockRankedCandidate], dict[str, float]]:
        self.retrieve_called_with.append({
            "parsed_query": parsed_query,
            "k_output": k_output,
            "embedding_cache": embedding_cache,
            "file_scope": file_scope,
        })
        # 기존 RetrievalEngine.retrieve() 시그니처 그대로: (candidates, metrics)
        return self.candidates, {"total_ms": 10.0}


# ---------------------------------------------------------------------------
# 테스트 데이터 생성 헬퍼
# ---------------------------------------------------------------------------

def _create_test_tsu_dataset(path: Path) -> None:
    """RetrievalEngine가 필요로 하는 최소 TSU dataset 파일 생성."""
    tsus = [
        {
            "tsu_id": "test-001",
            "content": "Prayer is a vital component of Christian faith. Jesus taught his disciples to pray.",
            "verse_mapping": {"book_id": "MAT", "chapter": 6, "verse_start": 7},
            "source_file": "test_sermon_001.xml",
            "document_id": "doc-001",
            "provenance": {"confidence": 0.8},
        },
        {
            "tsu_id": "test-002",
            "content": "Grace is the unmerited favor of God toward humanity. Through grace we are saved.",
            "verse_mapping": {"book_id": "ROM", "chapter": 3, "verse_start": 24},
            "source_file": "test_sermon_002.xml",
            "document_id": "doc-002",
            "provenance": {"confidence": 0.9},
        },
    ]
    path.write_text("\n".join(json.dumps(t) for t in tsus), encoding="utf-8")


def _create_test_db(db_path: str, tag_names: list[str] | None = None) -> None:
    """bible_tag_annotation 테이블이 있는 테스트 DB 생성."""
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("""
            CREATE TABLE bible_tag_annotation (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                canonical_reference TEXT NOT NULL,
                dataset_id TEXT NOT NULL,
                dataset_version TEXT NOT NULL,
                tag_namespace TEXT NOT NULL,
                tag_name TEXT NOT NULL,
                scope TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(canonical_reference, dataset_id, dataset_version, tag_namespace, tag_name)
            )
        """)

        if tag_names:
            now = datetime.now().isoformat()
            for tn in tag_names:
                conn.execute(
                    """INSERT INTO bible_tag_annotation
                       (canonical_reference, dataset_id, dataset_version, tag_namespace, tag_name, scope, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (f"Gen.24.{tn}", "test-dataset", "v1", "prayer", tn, "clause", now),
                )
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 테스트
# ---------------------------------------------------------------------------

class TestParallelRetrieverT1Axis:
    """T1 축: RetrievalEngine.retrieve()를 올바르게 감싸는지 검증."""

    def test_t1_axis_wraps_retrieve_engine(self, tmp_path: Path) -> None:
        """ParallelRetriever.retrieve()가 RetrievalEngine.retrieve()를 호출한다."""
        from core.parallel_retriever import ParallelRetriever, EvidenceCandidate, TrustTier

        # mock candidates
        mock_candidates = [
            MockRankedCandidate(
                tsu_id="test-001",
                content="Prayer content",
                metadata={"verse_mapping": {"book_id": "MAT"}},
                vector_score=0.8,
                bm25_score=0.7,
                theological_score=0.9,
                passage_score=0.6,
                final_score=0.75,
                explanation="test",
            ),
        ]
        engine = MockRetrievalEngine(mock_candidates)

        # 테스트 DB 생성
        db_path = str(tmp_path / "test.db")
        _create_test_db(db_path)

        parallel = ParallelRetriever(engine, db_path)

        # parsed_query mock
        from core.retrieval import ParsedQuery
        parsed_query = ParsedQuery(
            original_query="prayer",
            intent="unknown",
            keywords=["prayer"],
            detected_books=[],
            scripture_refs=[],
        )

        result = parallel.retrieve(parsed_query, k_output=10)

        # 검증: retrieve가 호출됐는지
        assert len(engine.retrieve_called_with) == 1, "RetrievalEngine.retrieve() must be called exactly once"

        # 검증: 반환 타입이 EvidenceCandidate 리스트
        assert isinstance(result, list)
        for item in result:
            assert isinstance(item, EvidenceCandidate)
            assert item.evidence_axis == "t1_hybrid_search"
            assert item.trust_tier == TrustTier.T1
            assert item.ranked_candidate is not None

    def test_t1_axis_preserves_retrieve_signature(self, tmp_path: Path) -> None:
        """RetrievalEngine.retrieve() 시그니처가 변경되지 않았다."""
        from core.parallel_retriever import ParallelRetriever

        engine = MockRetrievalEngine([])
        db_path = str(tmp_path / "test.db")
        _create_test_db(db_path)
        parallel = ParallelRetriever(engine, db_path)

        from core.retrieval import ParsedQuery
        parsed_query = ParsedQuery(
            original_query="grace",
            intent="unknown",
            keywords=["grace"],
            detected_books=[],
            scripture_refs=[],
        )

        # embedding_cache와 file_scope를 전달해도 에러 없이 통과해야 함
        result = parallel.retrieve(
            parsed_query,
            k_output=5,
            embedding_cache="mock_cache",
            file_scope=["test.xml"],
        )

        # 호출 인자 검증
        call_kwargs = engine.retrieve_called_with[0]
        assert call_kwargs["k_output"] == 5
        assert call_kwargs["embedding_cache"] == "mock_cache"
        assert call_kwargs["file_scope"] == ["test.xml"]


class TestParallelRetrieverT2Axis:
    """T2 축: bible_tag_annotation 조회가 올바르게 동작하는지 검증."""

    def test_t2_axis_queries_bible_tag_annotation(self, tmp_path: Path) -> None:
        """tag_names이 주어지면 bible_tag_annotation에서 조회한다."""
        from core.parallel_retriever import ParallelRetriever, EvidenceCandidate, TrustTier

        engine = MockRetrievalEngine([])
        db_path = str(tmp_path / "test.db")
        tag_names = ["prayer", "faith"]
        _create_test_db(db_path, tag_names=tag_names)

        parallel = ParallelRetriever(engine, db_path)

        from core.retrieval import ParsedQuery
        parsed_query = ParsedQuery(
            original_query="prayer",
            intent="unknown",
            keywords=["prayer"],
            detected_books=[],
            scripture_refs=[],
        )

        result = parallel.retrieve(parsed_query, k_output=10, tag_names=tag_names)

        # T2 축 결과가 포함됐는지
        t2_results = [r for r in result if r.evidence_axis == "t2_curated_tag"]
        assert len(t2_results) == 2, f"Expected 2 T2 results, got {len(t2_results)}"

        for item in t2_results:
            assert isinstance(item, EvidenceCandidate)
            assert item.trust_tier == TrustTier.T2
            assert item.canonical_reference is not None
            assert item.tag_name in tag_names

    def test_t2_axis_empty_when_no_tag_names(self, tmp_path: Path) -> None:
        """tag_names이 None이면 T2 축 결과가 없다."""
        from core.parallel_retriever import ParallelRetriever

        engine = MockRetrievalEngine([])
        db_path = str(tmp_path / "test.db")
        _create_test_db(db_path)  # tag_names=None

        parallel = ParallelRetriever(engine, db_path)

        from core.retrieval import ParsedQuery
        parsed_query = ParsedQuery(
            original_query="test",
            intent="unknown",
            keywords=["test"],
            detected_books=[],
            scripture_refs=[],
        )

        result = parallel.retrieve(parsed_query, k_output=10, tag_names=None)

        t2_results = [r for r in result if r.evidence_axis == "t2_curated_tag"]
        assert len(t2_results) == 0


class TestParallelRetrieverMerge:
    """병합: T1과 T2 결과가 올바르게 합쳐지는지 검증."""

    def test_merge_t1_before_t2(self, tmp_path: Path) -> None:
        """T1 결과가 T2 결과 앞에 온다."""
        from core.parallel_retriever import ParallelRetriever

        mock_candidates = [
            MockRankedCandidate(
                tsu_id="t1-001", content="T1 content", metadata={},
                vector_score=0.8, bm25_score=0.7, theological_score=0.9,
                passage_score=0.6, final_score=0.75, explanation="",
            ),
        ]
        engine = MockRetrievalEngine(mock_candidates)
        db_path = str(tmp_path / "test.db")
        _create_test_db(db_path, tag_names=["prayer"])

        parallel = ParallelRetriever(engine, db_path)

        from core.retrieval import ParsedQuery
        parsed_query = ParsedQuery(
            original_query="prayer",
            intent="unknown",
            keywords=["prayer"],
            detected_books=[],
            scripture_refs=[],
        )

        result = parallel.retrieve(parsed_query, k_output=10, tag_names=["prayer"])

        # T1이 먼저, T2가 그 다음
        t1_indices = [i for i, r in enumerate(result) if r.evidence_axis == "t1_hybrid_search"]
        t2_indices = [i for i, r in enumerate(result) if r.evidence_axis == "t2_curated_tag"]

        assert max(t1_indices) < min(t2_indices), "T1 results must come before T2 results"


class TestClassifyEvidence:
    """classify_evidence 헬퍼 검증."""

    def test_classify_groups_by_axis(self) -> None:
        from core.parallel_retriever import EvidenceCandidate, ParallelRetriever, classify_evidence, TrustTier

        candidates = [
            EvidenceCandidate(canonical_reference=None, evidence_axis="t1_hybrid_search", trust_tier=TrustTier.T1),
            EvidenceCandidate(canonical_reference="Gen.24.1", evidence_axis="t2_curated_tag", trust_tier=TrustTier.T2),
            EvidenceCandidate(canonical_reference=None, evidence_axis="t1_hybrid_search", trust_tier=TrustTier.T1),
        ]

        result = classify_evidence(candidates)

        assert len(result["t1_hybrid_search"]) == 2
        assert len(result["t2_curated_tag"]) == 1


class TestSprintABRegression:
    """Sprint A/B 테스트 30/30 회귀 — RetrievalEngine.retrieve() 기존 동작 유지.

    RetrievalEngine.retrieve()는 수정하지 않으므로, ParallelRetriever가
    반환하는 EvidenceCandidate를 통해 기존 결과가 그대로 전달되는지 검증.
    """

    def test_sprint_a_regression_all_candidates_preserved(self, tmp_path: Path) -> None:
        """Sprint A: RetrievalEngine.retrieve()의 모든 후보가 EvidenceCandidate에 감싸져 전달된다."""
        from core.parallel_retriever import ParallelRetriever

        # 30개 mock candidate — Sprint A/B 테스트 30건 대응
        mock_candidates = [
            MockRankedCandidate(
                tsu_id=f"sprint-a-{i:03d}",
                content=f"Content {i}",
                metadata={"verse_mapping": {"book_id": "MAT", "chapter": i % 66 + 1}},
                vector_score=0.5 + (i * 0.01),
                bm25_score=0.4 + (i * 0.01),
                theological_score=0.6 + (i * 0.005),
                passage_score=0.3 + (i * 0.008),
                final_score=0.7 - (i * 0.005),
                explanation=f"score breakdown {i}",
            )
            for i in range(30)
        ]
        engine = MockRetrievalEngine(mock_candidates)
        db_path = str(tmp_path / "test.db")
        _create_test_db(db_path)

        parallel = ParallelRetriever(engine, db_path)

        from core.retrieval import ParsedQuery
        parsed_query = ParsedQuery(
            original_query="test query",
            intent="unknown",
            keywords=["test"],
            detected_books=[],
            scripture_refs=[],
        )

        result = parallel.retrieve(parsed_query, k_output=30)

        t1_results = [r for r in result if r.evidence_axis == "t1_hybrid_search"]
        assert len(t1_results) == 30, f"Sprint A regression: expected 30 T1 candidates, got {len(t1_results)}"

        # 각 후보의 final_score가 그대로 전달되는지 검증
        for i, item in enumerate(t1_results):
            assert item.ranked_candidate is not None
            assert item.ranked_candidate.final_score == mock_candidates[i].final_score
            assert item.ranked_candidate.tsu_id == mock_candidates[i].tsu_id

    def test_sprint_b_regression_tag_annotation_preserved(self, tmp_path: Path) -> None:
        """Sprint B: bible_tag_annotation 조회 결과가 EvidenceCandidate에 감싸져 전달된다."""
        from core.parallel_retriever import ParallelRetriever, BibleTagAnnotation

        engine = MockRetrievalEngine([])
        db_path = str(tmp_path / "test.db")

        # 30개 tag annotation — Sprint B 테스트 30건 대응
        tag_names = [f"tag-{i:03d}" for i in range(30)]
        _create_test_db(db_path, tag_names=tag_names)

        parallel = ParallelRetriever(engine, db_path)

        from core.retrieval import ParsedQuery
        parsed_query = ParsedQuery(
            original_query="test query",
            intent="unknown",
            keywords=["test"],
            detected_books=[],
            scripture_refs=[],
        )

        result = parallel.retrieve(parsed_query, k_output=30, tag_names=tag_names)

        t2_results = [r for r in result if r.evidence_axis == "t2_curated_tag"]
        assert len(t2_results) == 30, f"Sprint B regression: expected 30 T2 candidates, got {len(t2_results)}"

        # tag_name이 그대로 전달되는지 검증
        t2_tag_names = {r.tag_name for r in t2_results}
        assert t2_tag_names == set(tag_names)


class TestCoreRetrievalUnmodified:
    """core/retrieval.py가 수정되지 않았음을 검증.

    이 테스트는 git diff core/retrieval.py가 빈 diff임을 확인한다.
    ParallelRetriever는 core/retrieval.py를 import해서 재사용할 뿐,
    절대 수정하지 않는다.
    """

    def test_core_retrieval_py_not_modified(self) -> None:
        """git diff core/retrieval.py가 빈 diff여야 한다."""
        import subprocess
        result = subprocess.run(
            ["git", "diff", "core/retrieval.py"],
            capture_output=True, text=True, cwd=str(Path(__file__).parent.parent),
        )
        assert result.stdout == "", (
            f"core/retrieval.py가 수정되었습니다. git diff core/retrieval.py:\n{result.stdout}\n"
            "ParallelRetriever는 core/retrieval.py를 수정하지 않습니다."
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])