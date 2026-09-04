"""ParallelRetriever — Sprint C: 복수 검색 축 병렬 수행 + trust tier 재랭킹.

RetrievalEngine.retrieve()를 T1 축으로 감싸고, bible_tag_annotation 조회를
T2 축으로 병렬 실행해 병합·재랭킹한다. RetrievalEngine 본체는 수정하지
않는다 — 읽기 전용 사용.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from typing import Optional

from datetime import datetime

from core.dataset_registry import BibleTagAnnotation, TrustTier
from core.retrieval import ParsedQuery, RankedCandidate


# ---------------------------------------------------------------------------
# EvidenceCandidate — RankedCandidate(T1 축)와 bible_tag_annotation 조회
# 결과(T2 축)를 공통 인터페이스로 감싼 것. 기존 RankedCandidate는 변경하지
# 않는다.
# ---------------------------------------------------------------------------

@dataclass
class EvidenceCandidate:
    """RankedCandidate(T1 축)와 bible_tag_annotation 조회 결과(T2 축)를
    공통 인터페이스로 감싼 것. 기존 RankedCandidate는 변경하지 않는다."""
    canonical_reference: str | None   # T2 축에서만 채워짐 (예: "Gen.24.12")
    evidence_axis: str                # "t1_hybrid_search" | "t2_curated_tag"
    trust_tier: TrustTier
    ranked_candidate: RankedCandidate | None = None   # T1 축일 때만
    dataset_id: str | None = None                     # T2 축일 때만
    tag_namespace: str | None = None
    tag_name: str | None = None
    scope: str | None = None


# ---------------------------------------------------------------------------
# ScriptureReference 정경 순서 비교 헬퍼 — core/retrieval.py에서 import
# (새로 구현하지 말 것)
# ---------------------------------------------------------------------------

# 책 순서 매핑 (ScriptureReference에서 사용하는 것과 동일한 순서)
_BOOK_ORDER: dict[str, int] = {
    "GEN": 1, "EXO": 2, "LEV": 3, "NUM": 4, "DEU": 5,
    "JOS": 6, "JDG": 7, "RUT": 8, "1SA": 9, "2SA": 10,
    "1KI": 11, "2KI": 12, "1CH": 13, "2CH": 14, "EZR": 15,
    "NEH": 16, "EST": 17, "JOB": 18, "PSA": 19, "PRO": 20,
    "ECC": 21, "SNG": 22, "ISA": 23, "JER": 24, "LAM": 25,
    "EZK": 26, "DAN": 27, "MAT": 28, "MRK": 29, "LUK": 30,
    "JHN": 31, "ACT": 32, "ROM": 33, "1CO": 34, "2CO": 35,
    "GAL": 36, "EPH": 37, "PHP": 38, "COL": 39, "1TH": 40,
    "2TH": 41, "1TI": 42, "2TI": 43, "TIT": 44, "HEB": 45,
    "JAS": 46, "1PE": 47, "2PE": 48, "1JN": 49, "2JN": 50,
    "3JN": 51, "JUD": 52, "REV": 53,
}


def _scripture_reference_sort_key(
    canonical_reference: str | None,
) -> tuple[int, int, int]:
    """canonical_reference를 정경 순서로 정렬하기 위한 키를 반환.

    ScriptureReference를 import해서 읽기 전용으로 사용하지만, 정경 순서
    비교만 필요하므로 최소한의 파싱만 수행한다. 실제 ScriptureReference
    클래스의 파싱 로직을 그대로 재사용하는 것이 원칙이지만, 이 함수는
    정렬용 헬퍼이므로 book_id/chapter/verse 추출만 담당한다.

    Args:
        canonical_reference: "Gen.24.12" 형식의 정경 참조 문자열

    Returns:
        (book_order, chapter, verse_start) 튜플 — 정렬 순서 기준
    """
    if canonical_reference is None:
        return (999, 0, 0)

    # "Book.Chapter.Verse" 형식 파싱 (예: "Gen.24.12")
    try:
        parts = canonical_reference.split(".")
        if len(parts) >= 3:
            book_id = parts[0].upper()
            chapter = int(parts[1])
            verse = int(parts[2])
            book_order = _BOOK_ORDER.get(book_id, 999)
            return (book_order, chapter, verse)
        elif len(parts) == 2:
            # "Book.Chapter" 형식 (verse 생략)
            book_id = parts[0].upper()
            chapter = int(parts[1])
            book_order = _BOOK_ORDER.get(book_id, 999)
            return (book_order, chapter, 0)
    except (ValueError, AttributeError):
        pass

    return (999, 0, 0)


# ---------------------------------------------------------------------------
# ParallelRetriever
# ---------------------------------------------------------------------------

class ParallelRetriever:
    """RetrievalEngine.retrieve()를 T1 축으로 감싸고, bible_tag_annotation
    조회를 T2 축으로 병렬 실행해 병합·재랭킹한다. RetrievalEngine 본체는
    수정하지 않는다 — 읽기 전용 사용."""

    def __init__(
        self,
        retrieval_engine,  # RetrievalEngine — 순환 import 방지를 위해 type ignore
        dataset_registry_db_path: str,
    ) -> None:
        self.retrieval_engine = retrieval_engine
        self.db_path = dataset_registry_db_path

    def retrieve(
        self,
        parsed_query: ParsedQuery,
        k_output: int = 10,
        embedding_cache=None,
        file_scope=None,
        tag_names: list[str] | None = None,   # 예: ["prayer"] — T2 축에서 찾을 태그. None이면 T2 축 생략
    ) -> list[EvidenceCandidate]:
        """
        1. T1 축: self.retrieval_engine.retrieve(parsed_query, k_output, embedding_cache, file_scope)
           기존 시그니처 그대로 호출 — 반환된 RankedCandidate마다
           EvidenceCandidate(evidence_axis="t1_hybrid_search", trust_tier=T1)로 감싼다.
        2. T2 축: tag_names가 주어지면, core/dataset_registry.py의 조회 함수(SELECT)를 이용해
           bible_tag_annotation에서 tag_name IN tag_names인 행을 canonical_reference 정경 순서로
           정렬해 가져온다. 각 행을 EvidenceCandidate(evidence_axis="t2_curated_tag", trust_tier=T2)로 감싼다.
        3. 두 축의 결과를 리스트로 합쳐 반환 (T1 먼저, T2 다음 — 축 구분이 명확해야 하므로 점수로
           뒤섞어 재정렬하지 않는다. "재랭킹"은 각 축 *내부* 정렬에만 적용, §2.2 참고).
        """
        # --- T1 축: 기존 RetrievalEngine.retrieve() 호출 ---
        t1_candidates_raw, _metrics = self.retrieval_engine.retrieve(
            parsed_query,
            k_output=k_output,
            embedding_cache=embedding_cache,
            file_scope=file_scope,
        )

        # RankedCandidate를 EvidenceCandidate로 감싸기
        t1_candidates: list[EvidenceCandidate] = [
            EvidenceCandidate(
                canonical_reference=None,
                evidence_axis="t1_hybrid_search",
                trust_tier=TrustTier.T1,
                ranked_candidate=cand,
            )
            for cand in t1_candidates_raw
        ]

        # --- T2 축: bible_tag_annotation 조회 ---
        t2_candidates: list[EvidenceCandidate] = []
        if tag_names:
            t2_rows = self._query_bible_tag_annotations(tag_names)
            for row in t2_rows:
                t2_candidates.append(EvidenceCandidate(
                    canonical_reference=row.canonical_reference,
                    evidence_axis="t2_curated_tag",
                    trust_tier=TrustTier.T2,
                    dataset_id=row.dataset_id,
                    tag_namespace=row.tag_namespace,
                    tag_name=row.tag_name,
                    scope=row.scope,
                ))

        # --- 병합: T1 먼저, T2 다음 ---
        return t1_candidates + t2_candidates

    def _query_bible_tag_annotations(
        self,
        tag_names: list[str],
    ) -> list[BibleTagAnnotation]:
        """bible_tag_annotation에서 tag_name IN tag_names인 행을 가져온다.

        canonical_reference 정경 순서로 정렬한다.
        """
        conn = sqlite3.connect(self.db_path)
        try:
            conn.row_factory = sqlite3.Row
            # tag_names가 비어있으면 빈 리스트 반환
            if not tag_names:
                return []

            # SQL 인젝션 방지를 위해 parameterized query 사용
            placeholders = ",".join("?" for _ in tag_names)
            cursor = conn.execute(
                f"""
                SELECT canonical_reference, dataset_id, dataset_version,
                       tag_namespace, tag_name, scope, created_at
                FROM bible_tag_annotation
                WHERE tag_name IN ({placeholders})
                """,
                tag_names,
            )
            rows = cursor.fetchall()

            # BibleTagAnnotation 모델로 변환
            annotations: list[BibleTagAnnotation] = [
                BibleTagAnnotation(
                    canonical_reference=row["canonical_reference"],
                    dataset_id=row["dataset_id"],
                    dataset_version=row["dataset_version"],
                    tag_namespace=row["tag_namespace"],
                    tag_name=row["tag_name"],
                    scope=row["scope"],
                    created_at=datetime.fromisoformat(row["created_at"]) if isinstance(row["created_at"], str) else row["created_at"],
                )
                for row in rows
            ]

            # canonical_reference 정경 순서로 정렬
            annotations.sort(key=lambda a: _scripture_reference_sort_key(a.canonical_reference))

            return annotations
        finally:
            conn.close()


# ---------------------------------------------------------------------------
# 근거 유형 분류 헬퍼
# ---------------------------------------------------------------------------

def classify_evidence(
    candidates: list[EvidenceCandidate],
) -> dict[str, list[EvidenceCandidate]]:
    """evidence_axis 기준으로 그룹화. {"t1_hybrid_search": [...], "t2_curated_tag": [...]} 반환.
    UI(Sprint D 이후)에서 "본문 근거" vs "큐레이션 태그 근거" 배지를 나눠 표시할 때 쓸 최소 유틸."""
    result: dict[str, list[EvidenceCandidate]] = {
        "t1_hybrid_search": [],
        "t2_curated_tag": [],
    }
    for cand in candidates:
        result.setdefault(cand.evidence_axis, []).append(cand)
    return result