"""ClaimGuard — Sprint D: 단위 테스트.

검증 계획 (Task Order §3):
1. 위험 표현 없는 claim_text → RiskLevel.NONE, 다른 필드 전부 기본값
2. 위험 표현 있음 + T1 근거 없음 → absolute_claim_blocked=True
3. 위험 표현 있음 + T2/T4만 있음 → absolute_claim_blocked=True, scope_qualifier_required=True
4. 위험 표현 있음 + T1 있음 + db_path=None(경쟁후보 탐색 불가) → absolute_claim_blocked=True
   (no_full_corpus_comparison_exists 케이스)
5. 위험 표현 있음 + T1 있음 + 경쟁후보 2개 이상 존재 → competing_candidates_found=True,
   absolute_claim_blocked 여부는 규칙 2d대로
6. detect_risk()가 사전의 모든 표현 각각에 대해 최소 1개는 매칭되는지 (전체 목록 순회 테스트)
7. _find_competing_candidates()가 Sprint B의 bible_tag_annotation 스키마와 정확히 맞물려 조회되는지
   (픽스처 DB로 실측)
"""

import os
import sqlite3
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
from dataclasses import dataclass, field
from enum import Enum

# DBMA 환경 설정
os.environ.setdefault("DBMA_DB_PATH", str(project_root / "output" / "test_dbma.db"))

from core.dataset_registry import TrustTier
from core.parallel_retriever import EvidenceCandidate
from core.claim_guard import ClaimGuard, ClaimGuardResult, RiskLevel, ABSOLUTE_SUPERLATIVE_TERMS


# ---------------------------------------------------------------------------
# 헬퍼: EvidenceCandidate 팩토리
# ---------------------------------------------------------------------------

def _make_evidence(
    trust_tier: TrustTier,
    canonical_reference: str | None = None,
    dataset_id: str | None = None,
    tag_name: str | None = None,
    scope: str | None = None,
) -> EvidenceCandidate:
    return EvidenceCandidate(
        canonical_reference=canonical_reference,
        evidence_axis="t1_hybrid_search" if trust_tier == TrustTier.T1 else "t2_curated_tag",
        trust_tier=trust_tier,
        ranked_candidate=None,
        dataset_id=dataset_id,
        tag_namespace=None,
        tag_name=tag_name,
        scope=scope,
    )


# ---------------------------------------------------------------------------
# 테스트 1: 위험 표현 없는 claim_text
# ---------------------------------------------------------------------------

class TestClaimGuardNoRisk:
    def test_no_risk_expression_returns_none(self):
        """위험 표현 없는 claim_text → RiskLevel.NONE, 다른 필드 전부 기본값"""
        guard = ClaimGuard()
        result = guard.evaluate("기도에 대해 알아보고 싶습니다.", [])
        assert result.risk_level == RiskLevel.NONE
        assert result.matched_terms == []
        assert result.scope_qualifier_required is False
        assert result.absolute_claim_blocked is False
        assert result.competing_candidates_found is False
        assert result.reason == ""
        assert result.suggested_wording is None


# ---------------------------------------------------------------------------
# 테스트 2: 위험 표현 있음 + T1 근거 없음
# ---------------------------------------------------------------------------

class TestClaimGuardRiskNoT1:
    def test_risk_expression_without_t1_evidence(self):
        """위험 표현 있음 + T2만 있음 → Rule 2b 실행 (scope_qualifier_required=True)"""
        guard = ClaimGuard()
        evidence = [
            _make_evidence(TrustTier.T2, canonical_reference="Gen.24.12", dataset_id="hunspell-korean", tag_name="prayer", scope="verse"),
        ]
        result = guard.evaluate("기도의 최초 사례는 Gen.24.12입니다.", evidence)
        assert result.risk_level == RiskLevel.HIGH
        assert "최초" in result.matched_terms
        assert result.absolute_claim_blocked is True
        assert result.scope_qualifier_required is True
        assert result.reason == "T2/T4 단독 근거로는 절대 주장 불가 — 데이터셋 범위 한정 필요"


# ---------------------------------------------------------------------------
# 테스트 3: 위험 표현 있음 + T2/T4만 있음
# ---------------------------------------------------------------------------

class TestClaimGuardRiskOnlyT2T4:
    def test_risk_expression_with_only_t2_evidence(self):
        """위험 표현 있음 + T2만 있음 → absolute_claim_blocked=True, scope_qualifier_required=True"""
        guard = ClaimGuard()
        evidence = [
            _make_evidence(
                TrustTier.T2, canonical_reference="Gen.24.12",
                dataset_id="hunspell-korean", tag_name="prayer", scope="verse",
            ),
        ]
        result = guard.evaluate("기도의 최초 사례는 Gen.24.12입니다.", evidence)
        assert result.risk_level == RiskLevel.HIGH
        assert "최초" in result.matched_terms
        assert result.absolute_claim_blocked is True
        assert result.scope_qualifier_required is True
        assert result.reason == "T2/T4 단독 근거로는 절대 주장 불가 — 데이터셋 범위 한정 필요"

    def test_risk_expression_with_only_t4_evidence(self):
        """위험 표현 있음 + T4만 있음 → absolute_claim_blocked=True, scope_qualifier_required=True"""
        guard = ClaimGuard()
        evidence = [
            _make_evidence(
                TrustTier.T4, canonical_reference="Gen.24.12",
                dataset_id="llm-inference", tag_name="inferred", scope="verse",
            ),
        ]
        result = guard.evaluate("기도의 최초 사례는 Gen.24.12입니다.", evidence)
        assert result.risk_level == RiskLevel.HIGH
        assert "최초" in result.matched_terms
        assert result.absolute_claim_blocked is True
        assert result.scope_qualifier_required is True

    def test_risk_expression_with_t2_and_t4(self):
        """위험 표현 있음 + T2+T4 혼합 → absolute_claim_blocked=True, scope_qualifier_required=True"""
        guard = ClaimGuard()
        evidence = [
            _make_evidence(
                TrustTier.T2, canonical_reference="Gen.24.12",
                dataset_id="hunspell-korean", tag_name="prayer", scope="verse",
            ),
            _make_evidence(
                TrustTier.T4, canonical_reference="Gen.24.12",
                dataset_id="llm-inference", tag_name="inferred", scope="verse",
            ),
        ]
        result = guard.evaluate("기도의 최초 사례는 Gen.24.12입니다.", evidence)
        assert result.risk_level == RiskLevel.HIGH
        assert "최초" in result.matched_terms
        assert result.absolute_claim_blocked is True
        assert result.scope_qualifier_required is True


# ---------------------------------------------------------------------------
# 테스트 4: 위험 표현 있음 + T1 있음 + db_path=None
# ---------------------------------------------------------------------------

class TestClaimGuardRiskT1NoDbPath:
    def test_risk_with_t1_but_no_db_path(self):
        """위험 표현 있음 + T1 있음 + db_path=None → absolute_claim_blocked=True"""
        guard = ClaimGuard(parallel_retriever_db_path=None)
        evidence = [
            _make_evidence(TrustTier.T1, canonical_reference=None),
        ]
        result = guard.evaluate("기도의 최초 사례는 Gen.24.12입니다.", evidence)
        assert result.risk_level == RiskLevel.HIGH
        assert "최초" in result.matched_terms
        assert result.absolute_claim_blocked is True
        assert result.competing_candidates_found is False
        assert "no_full_corpus_comparison_exists" in result.reason


# ---------------------------------------------------------------------------
# 테스트 5: 위험 표현 있음 + T1 있음 + 경쟁후보 2개 이상
# ---------------------------------------------------------------------------

class TestClaimGuardRiskT1WithCompetingCandidates:
    def _create_fixture_db(self, db_path: str) -> None:
        """bible_tag_annotation 픽스처 DB 생성"""
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
            # "prayer" 태그에 서로 다른 canonical_reference 3개
            fixtures = [
                ("Gen.24.12", "hunspell-korean", "1.0", "korean", "prayer", "verse", "2026-07-29T00:00:00"),
                ("Gen.24.42", "hunspell-korean", "1.0", "korean", "prayer", "verse", "2026-07-29T00:00:01"),
                ("Gen.24.60", "hunspell-korean", "1.0", "korean", "prayer", "verse", "2026-07-29T00:00:02"),
            ]
            conn.executemany(
                """INSERT INTO bible_tag_annotation
                   (canonical_reference, dataset_id, dataset_version, tag_namespace, tag_name, scope, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                fixtures,
            )
            conn.commit()
        finally:
            conn.close()

    def test_risk_with_t1_and_competing_candidates(self, tmp_path: Path):
        """위험 표현 있음 + T1 있음 + 경쟁후보 2개 이상 → competing_candidates_found=True"""
        db_path = str(tmp_path / "test_parallel_retriever.db")
        self._create_fixture_db(db_path)

        guard = ClaimGuard(parallel_retriever_db_path=db_path)
        # T2 evidence를 먼저 배치 — suggested_wording 생성용
        evidence = [
            _make_evidence(
                TrustTier.T2, canonical_reference="Gen.24.12",
                dataset_id="hunspell-korean", tag_name="prayer", scope="verse",
            ),
            _make_evidence(TrustTier.T1, canonical_reference=None),
        ]
        result = guard.evaluate("기도의 최초 사례는 Gen.24.12입니다.", evidence, tag_name="prayer")
        assert result.risk_level == RiskLevel.HIGH
        assert "최초" in result.matched_terms
        assert result.competing_candidates_found is True
        assert result.absolute_claim_blocked is False
        assert result.scope_qualifier_required is True
        assert result.reason == "경쟁 후보 확인됨 — 범위 한정 문구 필요"
        assert result.suggested_wording is not None

    def test_risk_with_t1_and_no_competing_candidates(self, tmp_path: Path):
        """위험 표현 있음 + T1 있음 + 경쟁후보 1개뿐 → absolute_claim_blocked=True"""
        db_path = str(tmp_path / "test_parallel_retriever.db")
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
            # "faith" 태그에 canonical_reference 1개뿐
            conn.execute(
                """INSERT INTO bible_tag_annotation
                   (canonical_reference, dataset_id, dataset_version, tag_namespace, tag_name, scope, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                ("Gen.15.6", "hunspell-korean", "1.0", "korean", "faith", "verse", "2026-07-29T00:00:00"),
            )
            conn.commit()
        finally:
            conn.close()

        guard = ClaimGuard(parallel_retriever_db_path=db_path)
        evidence = [
            _make_evidence(TrustTier.T1, canonical_reference=None),
            _make_evidence(
                TrustTier.T2, canonical_reference="Gen.15.6",
                dataset_id="hunspell-korean", tag_name="faith", scope="verse",
            ),
        ]
        result = guard.evaluate("믿음의 유일한 기준은 Gen.15.6입니다.", evidence, tag_name="faith")
        assert result.risk_level == RiskLevel.HIGH
        assert "유일" in result.matched_terms
        assert result.competing_candidates_found is False
        assert result.absolute_claim_blocked is True
        assert "no_full_corpus_comparison_exists" in result.reason


# ---------------------------------------------------------------------------
# 테스트 6: detect_risk() 전체 목록 순회 테스트
# ---------------------------------------------------------------------------

class TestDetectRiskFullList:
    def test_all_terms_match_at_least_once(self):
        """detect_risk()가 사전의 모든 표현 각각에 대해 최소 1개는 매칭되는지"""
        guard = ClaimGuard()
        for term in ABSOLUTE_SUPERLATIVE_TERMS:
            # 각_term을 포함한 문장으로 테스트
            claim = f"이것은 {term} 중요한 내용입니다."
            risk_level, matched = guard.detect_risk(claim)
            assert risk_level == RiskLevel.HIGH, f"'{term}'가 매칭되지 않음"
            assert term in matched, f"'{term}'가 matched에 없음"

    def test_empty_claim_returns_none(self):
        """빈 문자열 → RiskLevel.NONE"""
        guard = ClaimGuard()
        risk_level, matched = guard.detect_risk("")
        assert risk_level == RiskLevel.NONE
        assert matched == []


# ---------------------------------------------------------------------------
# 테스트 7: _find_competing_candidates() 픽스처 DB로 실측
# ---------------------------------------------------------------------------

class TestFindCompetingCandidates:
    def _create_fixture_db(self, db_path: str) -> None:
        """bible_tag_annotation 픽스처 DB 생성"""
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
            fixtures = [
                ("Gen.24.12", "hunspell-korean", "1.0", "korean", "prayer", "verse", "2026-07-29T00:00:00"),
                ("Gen.24.42", "hunspell-korean", "1.0", "korean", "prayer", "verse", "2026-07-29T00:00:01"),
                ("Gen.24.60", "hunspell-korean", "1.0", "korean", "prayer", "verse", "2026-07-29T00:00:02"),
                ("Gen.15.6", "hunspell-korean", "1.0", "korean", "faith", "verse", "2026-07-29T00:00:00"),
            ]
            conn.executemany(
                """INSERT INTO bible_tag_annotation
                   (canonical_reference, dataset_id, dataset_version, tag_namespace, tag_name, scope, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                fixtures,
            )
            conn.commit()
        finally:
            conn.close()

    def test_find_competing_returns_correct_count(self, tmp_path: Path):
        """_find_competing_candidates()가 픽스처 DB에서 정확한 개수 반환"""
        db_path = str(tmp_path / "test_competing.db")
        self._create_fixture_db(db_path)

        guard = ClaimGuard(parallel_retriever_db_path=db_path)
        # "prayer"는 3개, "faith"는 1개
        assert guard._find_competing_candidates("prayer") == 3
        assert guard._find_competing_candidates("faith") == 1
        assert guard._find_competing_candidates("nonexistent") == 0

    def test_find_competing_returns_zero_when_no_db(self):
        """db_path가 None이면 0 반환"""
        guard = ClaimGuard(parallel_retriever_db_path=None)
        assert guard._find_competing_candidates("prayer") == 0


# ---------------------------------------------------------------------------
# 테스트 8: suggested_wording 템플릿 검증
# ---------------------------------------------------------------------------

class TestSuggestedWording:
    def test_scope_statement_template(self):
        """T2/T4 단독 근거일 때 _scope_statement가 suggested_wording에 채워짐"""
        guard = ClaimGuard()
        evidence = [
            _make_evidence(
                TrustTier.T2, canonical_reference="Gen.24.12",
                dataset_id="hunspell-korean", tag_name="prayer", scope="verse",
            ),
        ]
        result = guard.evaluate("기도의 최초 사례는 Gen.24.12입니다.", evidence)
        assert result.suggested_wording is not None
        assert "hunspell-korean" in result.suggested_wording
        assert "prayer" in result.suggested_wording
        assert "Gen.24.12" in result.suggested_wording

    def test_scoped_conclusion_statement_template(self):
        """경쟁후보 확인 시 _scoped_conclusion_statement가 suggested_wording에 채워짐"""
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
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
                fixtures = [
                    ("Gen.24.12", "hunspell-korean", "1.0", "korean", "prayer", "verse", "2026-07-29T00:00:00"),
                    ("Gen.24.42", "hunspell-korean", "1.0", "korean", "prayer", "clause", "2026-07-29T00:00:01"),
                    ("Gen.24.60", "hunspell-korean", "1.0", "korean", "prayer", "discourse_unit", "2026-07-29T00:00:02"),
                ]
                conn.executemany(
                    """INSERT INTO bible_tag_annotation
                       (canonical_reference, dataset_id, dataset_version, tag_namespace, tag_name, scope, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    fixtures,
                )
                conn.commit()
            finally:
                conn.close()

            guard = ClaimGuard(parallel_retriever_db_path=db_path)
            # T2 evidence를 먼저 배치 — suggested_wording 생성용
            evidence = [
                _make_evidence(
                    TrustTier.T2, canonical_reference="Gen.24.12",
                    dataset_id="hunspell-korean", tag_name="prayer", scope="verse",
                ),
                _make_evidence(TrustTier.T1, canonical_reference=None),
            ]
            result = guard.evaluate("기도의 최초 사례는 Gen.24.12입니다.", evidence, tag_name="prayer")
            assert result.suggested_wording is not None
            assert "Gen.24.12" in result.suggested_wording
            assert "가장 이른 사례 중 하나로 볼 수 있다" in result.suggested_wording
        finally:
            os.unlink(db_path)


# ---------------------------------------------------------------------------
# 테스트 9: 여러 위험 표현이 동시에 나타나는 경우
# ---------------------------------------------------------------------------

class TestMultipleRiskTerms:
    def test_multiple_risk_terms_matched(self):
        """여러 위험 표현이 동시에 나타나면 모두 매칭"""
        guard = ClaimGuard()
        claim = "기도의 최초 그리고 유일한 사례는 Gen.24.12이며, 반드시 반드시 정확하다."
        risk_level, matched = guard.detect_risk(claim)
        assert risk_level == RiskLevel.HIGH
        assert "최초" in matched
        assert "유일" in matched

    def test_evaluate_with_multiple_risk_terms(self):
        """여러 위험 표현이 있는 claim_text에 대한 evaluate"""
        guard = ClaimGuard()
        evidence = [
            _make_evidence(TrustTier.T2, canonical_reference="Gen.24.12", dataset_id="hunspell-korean", tag_name="prayer", scope="verse"),
        ]
        result = guard.evaluate("기도의 최초 그리고 유일한 사례는 Gen.24.12입니다.", evidence)
        assert result.risk_level == RiskLevel.HIGH
        assert "최초" in result.matched_terms
        assert "유일" in result.matched_terms
        assert result.absolute_claim_blocked is True
        assert result.scope_qualifier_required is True


# ---------------------------------------------------------------------------
# 테스트 10: T1 + T2 혼합 근거 (경쟁후보 없음)
# ---------------------------------------------------------------------------

class TestClaimGuardMixedEvidence:
    def test_t1_plus_t2_without_competing(self, tmp_path: Path):
        """T1 + T2 혼합 근거 + 경쟁후보 1개 → absolute_claim_blocked=True"""
        db_path = str(tmp_path / "test_mixed.db")
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
            conn.execute(
                """INSERT INTO bible_tag_annotation
                   (canonical_reference, dataset_id, dataset_version, tag_namespace, tag_name, scope, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                ("Gen.24.12", "hunspell-korean", "1.0", "korean", "prayer", "verse", "2026-07-29T00:00:00"),
            )
            conn.commit()
        finally:
            conn.close()

        guard = ClaimGuard(parallel_retriever_db_path=db_path)
        evidence = [
            _make_evidence(TrustTier.T1, canonical_reference=None),
            _make_evidence(
                TrustTier.T2, canonical_reference="Gen.24.12",
                dataset_id="hunspell-korean", tag_name="prayer", scope="verse",
            ),
        ]
        result = guard.evaluate("기도의 최초 사례는 Gen.24.12입니다.", evidence, tag_name="prayer")
        assert result.risk_level == RiskLevel.HIGH
        assert "최초" in result.matched_terms
        assert result.competing_candidates_found is False
        assert result.absolute_claim_blocked is True
        assert "no_full_corpus_comparison_exists" in result.reason


# ---------------------------------------------------------------------------
# 테스트 11: T1 + T3 혼합 근거
# ---------------------------------------------------------------------------

class TestClaimGuardT1T3Evidence:
    def test_t1_plus_t3_without_db_path(self):
        """T1 + T3 혼합 근거 + db_path=None → absolute_claim_blocked=True"""
        guard = ClaimGuard(parallel_retriever_db_path=None)
        evidence = [
            _make_evidence(TrustTier.T1, canonical_reference=None),
            _make_evidence(TrustTier.T3, canonical_reference="Gen.24.12"),
        ]
        result = guard.evaluate("기도의 최초 사례는 Gen.24.12입니다.", evidence)
        assert result.risk_level == RiskLevel.HIGH
        assert "최초" in result.matched_terms
        assert result.absolute_claim_blocked is True
        assert "no_full_corpus_comparison_exists" in result.reason


# ---------------------------------------------------------------------------
# 테스트 12: 빈 evidence 리스트
# ---------------------------------------------------------------------------

class TestClaimGuardEmptyEvidence:
    def test_empty_evidence_with_risk(self):
        """빈 evidence + 위험 표현 → only_t2_or_t4=True이므로 Rule 2b 실행"""
        guard = ClaimGuard()
        result = guard.evaluate("기도의 최초 사례는 Gen.24.12입니다.", [])
        assert result.risk_level == RiskLevel.HIGH
        assert result.absolute_claim_blocked is True
        assert result.scope_qualifier_required is True
        assert result.reason == "T2/T4 단독 근거로는 절대 주장 불가 — 데이터셋 범위 한정 필요"


# ---------------------------------------------------------------------------
# 테스트 13: 모든 위험 표현 사전 검증
# ---------------------------------------------------------------------------

class TestAbsoluteSuperlativeTermsList:
    def test_list_not_empty(self):
        """ABSOLUTE_SUPERLATIVE_TERMS가 비어있지 않음"""
        assert len(ABSOLUTE_SUPERLATIVE_TERMS) > 0

    def test_all_strings(self):
        """모든 항목이 문자열임"""
        for term in ABSOLUTE_SUPERLATIVE_TERMS:
            assert isinstance(term, str)
            assert len(term) > 0