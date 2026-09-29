"""core/grounded_synthesis_input.py Phase 4 tests.

Grounded Synthesis Phase 4: SynthesisInput Boundary
Tests cover:
    AC1: included + excluded = pool의 전체 evidence_id 집합 (누락·중복 없음)
    AC2: pool <= max_evidence -> truncated=False, excluded=[]
    AC3: pool > max_evidence -> truncated=True, len(included)==max_evidence
    AC4: 라운드로빈 순서 검증
    AC5: 중복 evidence_id는 included에 1회만 등장
    AC6: prompt_text에 included 텍스트 포함, excluded 텍스트 미포함
    AC7: source_file=None -> "[출처: 미상]"
    AC8: 점수 읽기/비교 코드 없음 (grep 검증)
    AC9: 금지 import 없음 (ADR-036 B9)

ABSOLUTE RULES:
- EvidencePool, AssemblyManifest는 기존 모듈을 사용 (수정 금지)
- Evidence 객체는 실제 데이터 구조를 따름
"""

import subprocess
from pathlib import Path
from typing import Any

import pytest

from core.evidence_assembly import AssemblyManifest, QuerySpec
from core.evidence_model import Evidence
from core.evidence_pool import EvidencePool
from core.grounded_synthesis_input import SynthesisInput, build_synthesis_input


_PROJECT_ROOT = Path(__file__).resolve().parents[1]  # tests/ 의 부모 = 저장소 루트


# ============================================================
# FIXTURES — 기존 아키텍처의 실제 데이터 구조 사용
# ============================================================

def _make_evidence(
    eid: str,
    text: str,
    source_file: str | None = "test_doc.jsonl",
    document_title: str | None = "Test Document",
) -> Evidence:
    """Evidence 객체를 생성하는 헬퍼 (fixture용)."""
    return Evidence(
        evidence_id=eid,
        corpus_type="default",
        text=text,
        source_file=source_file,
        document_title=document_title,
        chunk_id=f"chunk_{eid}",
        retrieval_query="test_query",
        retrieval_method="bm25",
        bm25_score=0.5,
        final_score=0.7,
    )


# AC4 라운드로빈 검증용: 질의 A [e1,e2,e3], 질의 B [e4,e5]
EVIDENCE_A1 = _make_evidence("e1", "Text A1 - first evidence from query A.")
EVIDENCE_A2 = _make_evidence("e2", "Text A2 - second evidence from query A.")
EVIDENCE_A3 = _make_evidence("e3", "Text A3 - third evidence from query A.")
EVIDENCE_B1 = _make_evidence("e4", "Text B1 - first evidence from query B.")
EVIDENCE_B2 = _make_evidence("e5", "Text B2 - second evidence from query B.")

QUERY_A = QuerySpec(query="Query A", role="primary", order=0)
QUERY_B = QuerySpec(query="Query B", role="expanded", order=1)


# ============================================================
# AC1: included + excluded = pool의 전체 evidence_id 집합
# ============================================================

class TestAC1_IncludedExcludedCompleteness:
    def test_ac1_all_evidence_accounted_for(self):
        """AC1: included와 excluded를 합치면 pool의 전체 evidence_id 집합과 정확히 같다."""
        pool = EvidencePool()
        pool.add(EVIDENCE_A1)
        pool.add(EVIDENCE_A2)
        pool.add(EVIDENCE_B1)

        manifest = AssemblyManifest(
            by_query_order=[
                (QUERY_A, ["e1", "e2"]),
                (QUERY_B, ["e4"]),
            ],
            evidence_to_queries={
                "e1": ["Query A"],
                "e2": ["Query A"],
                "e4": ["Query B"],
            },
        )

        result = build_synthesis_input(pool, manifest, max_evidence=10)

        pool_ids = {ev.evidence_id for ev in pool.all()}
        combined = set(result.included_evidence_ids) | set(result.excluded_evidence_ids)
        assert combined == pool_ids, f"불일치: pool={pool_ids}, combined={combined}"
        # 중복 없음 확인
        assert len(result.included_evidence_ids) == len(set(result.included_evidence_ids))
        assert len(result.excluded_evidence_ids) == len(set(result.excluded_evidence_ids))


# ============================================================
# AC2: pool <= max_evidence -> truncated=False, excluded=[]
# ============================================================

class TestAC2_NoTruncation:
    def test_ac2_pool_smaller_than_max(self):
        """AC2: max_evidence보다 pool이 작으면 truncated==False, excluded==[]."""
        pool = EvidencePool()
        pool.add(EVIDENCE_A1)
        pool.add(EVIDENCE_B1)

        manifest = AssemblyManifest(
            by_query_order=[
                (QUERY_A, ["e1"]),
                (QUERY_B, ["e4"]),
            ],
            evidence_to_queries={"e1": ["Query A"], "e4": ["Query B"]},
        )

        result = build_synthesis_input(pool, manifest, max_evidence=10)

        assert result.truncated is False
        assert result.excluded_evidence_ids == []
        assert len(result.included_evidence_ids) == 2

    def test_ac2_pool_equal_to_max(self):
        """AC2: pool 크기와 max_evidence가 같으면 truncated==False."""
        pool = EvidencePool()
        pool.add(EVIDENCE_A1)

        manifest = AssemblyManifest(
            by_query_order=[(QUERY_A, ["e1"])],
            evidence_to_queries={"e1": ["Query A"]},
        )

        result = build_synthesis_input(pool, manifest, max_evidence=1)

        assert result.truncated is False
        assert result.excluded_evidence_ids == []


# ============================================================
# AC3: pool > max_evidence -> truncated=True, len(included)==max_evidence
# ============================================================

class TestAC3_Truncation:
    def test_ac3_pool_larger_than_max(self):
        """AC3: max_evidence보다 pool이 크면 truncated==True, len(included)==max_evidence."""
        pool = EvidencePool()
        pool.add(EVIDENCE_A1)
        pool.add(EVIDENCE_A2)
        pool.add(EVIDENCE_B1)

        manifest = AssemblyManifest(
            by_query_order=[
                (QUERY_A, ["e1", "e2"]),
                (QUERY_B, ["e4"]),
            ],
            evidence_to_queries={"e1": ["Query A"], "e2": ["Query A"], "e4": ["Query B"]},
        )

        result = build_synthesis_input(pool, manifest, max_evidence=2)

        assert result.truncated is True
        assert len(result.included_evidence_ids) == 2
        assert len(result.excluded_evidence_ids) > 0


# ============================================================
# AC4: 라운드로빈 순서 검증
# ============================================================

class TestAC4_RoundRobinOrder:
    def test_ac4_roundrobin_sequence(self):
        """AC4: 질의 A [e1,e2,e3], 질의 B [e4,e5], max_evidence=3 -> [e1, e4, e2]."""
        pool = EvidencePool()
        pool.add(EVIDENCE_A1)
        pool.add(EVIDENCE_A2)
        pool.add(EVIDENCE_A3)
        pool.add(EVIDENCE_B1)
        pool.add(EVIDENCE_B2)

        manifest = AssemblyManifest(
            by_query_order=[
                (QUERY_A, ["e1", "e2", "e3"]),
                (QUERY_B, ["e4", "e5"]),
            ],
            evidence_to_queries={
                "e1": ["Query A"], "e2": ["Query A"], "e3": ["Query A"],
                "e4": ["Query B"], "e5": ["Query B"],
            },
        )

        result = build_synthesis_input(pool, manifest, max_evidence=3)

        assert result.included_evidence_ids == ["e1", "e4", "e2"]


# ============================================================
# AC5: 같은 evidence_id를 여러 질의가 찾아도 included에 1회만 등장
# ============================================================

class TestAC5_DuplicateEvidenceId:
    def test_ac5_same_eid_across_queries(self):
        """AC5: 같은 evidence_id를 여러 질의가 찾아도 included에 1회만 등장."""
        pool = EvidencePool()
        pool.add(EVIDENCE_A1)

        # e1이 두 질의 모두에 나타남
        manifest = AssemblyManifest(
            by_query_order=[
                (QUERY_A, ["e1", "e2"]),
                (QUERY_B, ["e1", "e3"]),
            ],
            evidence_to_queries={
                "e1": ["Query A", "Query B"],
                "e2": ["Query A"],
                "e3": ["Query B"],
            },
        )

        result = build_synthesis_input(pool, manifest, max_evidence=10)

        assert result.included_evidence_ids.count("e1") == 1
        # e1이 첫 번째로 등장해야 (QUERY_A가 먼저)
        assert result.included_evidence_ids[0] == "e1"


# ============================================================
# AC6: prompt_text에 included 텍스트 포함, excluded 텍스트 미포함
# ============================================================

class TestAC6_PromptTextContent:
    def test_ac6_included_text_present(self):
        """AC6: prompt_text에 included_evidence_ids의 모든 텍스트가 등장."""
        pool = EvidencePool()
        pool.add(EVIDENCE_A1)
        pool.add(EVIDENCE_B1)

        manifest = AssemblyManifest(
            by_query_order=[
                (QUERY_A, ["e1"]),
                (QUERY_B, ["e4"]),
            ],
            evidence_to_queries={"e1": ["Query A"], "e4": ["Query B"]},
        )

        result = build_synthesis_input(pool, manifest, max_evidence=2)

        assert "Text A1" in result.prompt_text
        assert "Text B1" in result.prompt_text

    def test_ac6_excluded_text_absent(self):
        """AC6: excluded_evidence_ids의 텍스트는 prompt_text에 등장하지 않음."""
        pool = EvidencePool()
        pool.add(EVIDENCE_A1)
        pool.add(EVIDENCE_A2)

        manifest = AssemblyManifest(
            by_query_order=[
                (QUERY_A, ["e1", "e2"]),
            ],
            evidence_to_queries={"e1": ["Query A"], "e2": ["Query A"]},
        )

        result = build_synthesis_input(pool, manifest, max_evidence=1)

        assert "Text A1" in result.prompt_text
        assert "Text A2" not in result.prompt_text


# ============================================================
# AC7: source_file=None -> "[출처: 미상]"
# ============================================================

class TestAC7_MissingSourceLabel:
    def test_ac7_none_source_file(self):
        """AC7: Evidence.provenance.source_file이 None인 항목의 prompt_text에는 '[출처: 미상]'."""
        ev_no_source = _make_evidence(
            "e_no_src",
            "Text with no source.",
            source_file=None,
            document_title=None,
        )

        pool = EvidencePool()
        pool.add(ev_no_source)

        manifest = AssemblyManifest(
            by_query_order=[(QUERY_A, ["e_no_src"])],
            evidence_to_queries={"e_no_src": ["Query A"]},
        )

        result = build_synthesis_input(pool, manifest, max_evidence=1)

        assert "[출처: 미상]" in result.prompt_text


# ============================================================
# AC8: 점수 읽기/비교 코드 없음 (grep 검증)
# ============================================================

class TestAC8_NoScoreAccess:
    def test_ac8_grep_no_score_access(self):
        """AC8: grep으로 .final_score, .retrieval_score, sorted(, sort( 부재 확인."""
        result = subprocess.run(
            [
                "grep", "-nE",
                r"\.final_score|\.retrieval_score|\.bm25_score|\.theological_score|\.passage_score|"
                r"sorted\(|\.sort\(",
                str(_PROJECT_ROOT / "core" / "grounded_synthesis_input.py"),
            ],
            capture_output=True,
            text=True,
        )
        # grep은 매칭되면 0, 없으면 1 반환
        assert result.returncode == 1, (
            f"AC8 실패: 점수 접근 코드가 발견됨:\n{result.stdout}"
        )


# ============================================================
# AC9: 금지 import 없음 (ADR-036 B9)
# ============================================================

class TestAC9_NoForbiddenImports:
    def test_ac9_grep_no_forbidden_imports(self):
        """AC9: import ollama, retrieval 클래스 import가 이 파일에 없음."""
        result = subprocess.run(
            [
                "grep", "-nE",
                r"^import\s+(ollama|qdrant_client|tantivy|requests|httpx|urllib|subprocess|socket)|"
                r"^from\s+(ollama|qdrant_client|tantivy|requests|httpx|urllib|subprocess|socket)|"
                r"QueryProcessor|HybridQueryProcessor|RetrievalEngine|HybridRetriever|CandidateGenerator|GenerationService",
                str(_PROJECT_ROOT / "core" / "grounded_synthesis_input.py"),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1, (
            f"AC9 실패: 금지 import가 발견됨:\n{result.stdout}"
        )


# ============================================================
# SynthesisInput 구조 검증
# ============================================================

class TestSynthesisInputStructure:
    def test_synthesis_input_is_frozen_dataclass(self):
        """SynthesisInput이 frozen dataclass인지 확인."""
        assert hasattr(SynthesisInput, "__dataclass_fields__")
        # frozen=True면 __setattr__이 금지됨
        si = SynthesisInput(
            query_specs=[QUERY_A],
            included_evidence_ids=["e1"],
            excluded_evidence_ids=[],
            truncated=False,
            prompt_text="test",
        )
        with pytest.raises(Exception):
            si.included_evidence_ids = ["e2"]

    def test_synthesis_input_all_fields_present(self):
        """SynthesisInput이 ADR-036 B8의 모든 필드를 갖는지 확인."""
        from dataclasses import fields

        field_names = {f.name for f in fields(SynthesisInput)}
        expected = {"query_specs", "included_evidence_ids", "excluded_evidence_ids", "truncated", "prompt_text"}
        assert field_names == expected


# ============================================================
# build_synthesis_input 경로 검증
# ============================================================

class TestBuildSynthesisInputEdgeCases:
    def test_empty_pool(self):
        """빈 pool에서 호출하면 included=[], truncated=False."""
        pool = EvidencePool()

        manifest = AssemblyManifest(
            by_query_order=[(QUERY_A, [])],
            evidence_to_queries={},
        )

        result = build_synthesis_input(pool, manifest, max_evidence=5)

        assert result.included_evidence_ids == []
        assert result.excluded_evidence_ids == []
        assert result.truncated is False
        assert result.prompt_text == ""

    def test_invalid_max_evidence(self):
        """max_evidence <= 0은 ValueError."""
        pool = EvidencePool()
        manifest = AssemblyManifest(
            by_query_order=[(QUERY_A, ["e1"])],
            evidence_to_queries={"e1": ["Query A"]},
        )

        with pytest.raises(ValueError, match="max_evidence must be > 0"):
            build_synthesis_input(pool, manifest, max_evidence=0)

        with pytest.raises(ValueError, match="max_evidence must be > 0"):
            build_synthesis_input(pool, manifest, max_evidence=-1)

    def test_query_specs_preserved(self):
        """query_specs가 manifest의 by_query_order와 일치."""
        pool = EvidencePool()
        pool.add(EVIDENCE_A1)

        manifest = AssemblyManifest(
            by_query_order=[
                (QUERY_A, ["e1"]),
                (QUERY_B, []),
            ],
            evidence_to_queries={"e1": ["Query A"]},
        )

        result = build_synthesis_input(pool, manifest, max_evidence=5)

        spec_queries = [qs.query for qs in result.query_specs]
        assert spec_queries == ["Query A", "Query B"]
