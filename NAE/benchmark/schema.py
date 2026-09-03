"""NAE Benchmark Schema — Question Unit 정의

자동 정답 생성 금지. 모든 값은 수동 입력 또는 후속 단계에서 생성.

확장 스키마 (C1-TASK-ORDER-037):
- gold_tsu_ids: retrieval ground truth (TSU ID 공간 기준)
- question_type / difficulty / theology_area / review_status: 메타 필드
- metadata: tsu_schema_version, collector_version, canonical_version
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ------------------------------------------------------------------
# Schema Constants
# ------------------------------------------------------------------

# 질문 유형 (수동 확정 값)
QUESTION_TYPES: List[str] = [
    "concept",       # 개념 이해
    "scripture",     # 성경 근거
    "doctrine",      # 교리 비교
    "historical",    # 역사적 문맥
    "application",   # 적용
    "comparison",    # 비교 분석
    "other",         # 기타
]

# 난이도 (수동 확정 값)
DIFFICULTY_LEVELS: List[str] = [
    "beginner",
    "intermediate",
    "advanced",
    "scholarly",
]

# 검토 상태
REVIEW_STATUSES: List[str] = [
    "draft",
    "review",
    "approved",
    "rejected",
]

# Gold validity diagnostic (HQ-C1-DIRECTIVE-NAE-PHASE5.1-REMEDIATION-004)
GOLD_VALIDITY_STATUSES: List[str] = [
    "VALID",           # gold_tsu_ids 가 비어 있고 중복 없음
    "INVALID_GOLD",    # gold_tsu_ids 가 None, 누락, 또는 빈 list
    "DUPLICATE_GOLD",  # gold_tsu_ids 에 중복이 있음
]


# ------------------------------------------------------------------
# Data Classes
# ------------------------------------------------------------------

@dataclass
class BenchmarkQuestion:
    """검색 질문 단위."""

    text: str = ""
    language: str = "ko"  # "ko" | "en"
    question_type: str = "other"  # QUESTION_TYPES 중 하나
    theology_area: str = ""  # THEOLOGY_AREA_CATEGORIES 중 하나 (빈 값 가능)


@dataclass
class BenchmarkExpected:
    """예측 정답 정보 (수동 입력).

    DEPRECATED: gold_tsu_ids는 BenchmarkItem.gold_tsu_ids로 canonical 이동.
    loader가 legacy JSONL에서 역직렬화할 때만 사용됩니다.
    """

    gold_tsu_ids: List[str] = field(
        default_factory=list,
        metadata={"deprecated": True, "legacy_alias": "BenchmarkItem.gold_tsu_ids"},
    )
    required_concepts: List[str] = field(default_factory=list)
    expected_scriptures: List[str] = field(default_factory=list)
    expected_doctrine: str = ""


@dataclass
class BenchmarkRetrieval:
    """검색 설정."""

    top_k: int = 5


@dataclass
class BenchmarkEvaluation:
    """평가 결과."""

    status: str = "pending"  # "pending" | "passed" | "failed"
    scores: Dict[str, float] = field(default_factory=dict)
    notes: str = ""


@dataclass
class BenchmarkMetadata:
    """메타데이터."""

    created_version: str = ""
    source: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    tsu_schema_version: str = ""
    collector_version: str = ""
    canonical_version: str = ""


@dataclass
class BenchmarkItem:
    """벤치마크 질문 단위 — 전체 레코드."""

    benchmark_id: str = ""
    question: BenchmarkQuestion = field(default_factory=BenchmarkQuestion)
    expected: BenchmarkExpected = field(default_factory=BenchmarkExpected)
    retrieval: BenchmarkRetrieval = field(default_factory=BenchmarkRetrieval)
    evaluation: BenchmarkEvaluation = field(default_factory=BenchmarkEvaluation)
    metadata: BenchmarkMetadata = field(default_factory=BenchmarkMetadata)

    # retrieved_tsu_ids: 검색 결과로 얻은 TSU ID 목록 (평가 runner 에서 채움)
    retrieved_tsu_ids: List[str] = field(default_factory=list)
    retrieved_scores: List[float] = field(default_factory=list)

    # gold standard ground truth — TSU ID 공간 기준
    gold_tsu_ids: List[str] = field(default_factory=list)

    # 난이도 (수동 입력)
    difficulty: str = "beginner"  # DIFFICULTY_LEVELS 중 하나

    # 검토 상태 (수동 입력)
    review_status: str = "draft"  # REVIEW_STATUSES 중 하나

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 직렬화."""
        return {
            "benchmark_id": self.benchmark_id,
            "question": asdict(self.question),
            "expected": asdict(self.expected),
            "retrieval": asdict(self.retrieval),
            "evaluation": asdict(self.evaluation),
            "metadata": asdict(self.metadata),
            "retrieved_tsu_ids": self.retrieved_tsu_ids,
            "retrieved_scores": self.retrieved_scores,
            "gold_tsu_ids": self.gold_tsu_ids,
            "difficulty": self.difficulty,
            "review_status": self.review_status,
        }

    def to_json(self, indent: int = 2) -> str:
        """JSON 문자열로 직렬화."""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    # ------------------------------------------------------------------
    # Factory Methods
    # ------------------------------------------------------------------

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> BenchmarkItem:
        """딕셔너리에서 역직렬화."""
        return cls(
            benchmark_id=data.get("benchmark_id", ""),
            question=BenchmarkQuestion(**data.get("question", {})),
            expected=BenchmarkExpected(**data.get("expected", {})),
            retrieval=BenchmarkRetrieval(**data.get("retrieval", {})),
            evaluation=BenchmarkEvaluation(**data.get("evaluation", {})),
            metadata=BenchmarkMetadata(**data.get("metadata", {})),
            retrieved_tsu_ids=data.get("retrieved_tsu_ids", []),
            retrieved_scores=data.get("retrieved_scores", []),
            gold_tsu_ids=data.get("gold_tsu_ids", []),
            difficulty=data.get("difficulty", "beginner"),
            review_status=data.get("review_status", "draft"),
        )

    @classmethod
    def from_json(cls, json_str: str) -> BenchmarkItem:
        """JSON 문자열에서 역직렬화."""
        return cls.from_dict(json.loads(json_str))

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self) -> List[str]:
        """필수 필드 검증. 문제 목록을 반환 (비어으면 유효)."""
        errors: List[str] = []

        if not self.benchmark_id:
            errors.append("benchmark_id is required")

        if not self.question.text.strip():
            errors.append("question.text is required")

        if self.question.language not in ("ko", "en"):
            errors.append(
                f"question.language must be 'ko' or 'en', got '{self.question.language}'"
            )

        if self.question.question_type not in QUESTION_TYPES:
            errors.append(
                f"question.question_type must be one of {QUESTION_TYPES}, "
                f"got '{self.question.question_type}'"
            )

        if self.retrieval.top_k < 1:
            errors.append("retrieval.top_k must be >= 1")

        if self.difficulty not in DIFFICULTY_LEVELS:
            errors.append(
                f"difficulty must be one of {DIFFICULTY_LEVELS}, got '{self.difficulty}'"
            )

        if self.review_status not in REVIEW_STATUSES:
            errors.append(
                f"review_status must be one of {REVIEW_STATUSES}, got '{self.review_status}'"
            )

        # theology_area: 빈 값("")은 허용, 값이 있으면 THEOLOGY_AREA_CATEGORIES에 속해야 함
        if self.question.theology_area != "":
            from NAE.benchmark.config import THEOLOGY_AREA_CATEGORIES

            if self.question.theology_area not in THEOLOGY_AREA_CATEGORIES:
                errors.append(
                    f"question.theology_area must be '' or one of {THEOLOGY_AREA_CATEGORIES}, "
                    f"got '{self.question.theology_area}'"
                )

        # gold_tsu_ids 중복 검사
        if len(self.gold_tsu_ids) != len(set(self.gold_tsu_ids)):
            errors.append("gold_tsu_ids contains duplicates")

        return errors

    def validate_referential_integrity(
        self, known_tsu_ids: Optional[set] = None
    ) -> List[str]:
        """gold_tsu_ids 가 known_tsu_ids 에 존재하는지 검증.

        Parameters
        ----------
        known_tsu_ids : set or None
            실제 TSU 데이터셋의 모든 ID 집합.
            None 이면 검증을 건너뛴다.

        Returns
        -------
        List[str]
            검증 오류 목록.
        """
        if known_tsu_ids is None:
            return []

        errors: List[str] = []
        for tsu_id in self.gold_tsu_ids:
            if tsu_id not in known_tsu_ids:
                errors.append(f"gold_tsu_id '{tsu_id}' not found in known TSU IDs")
        return errors


# ------------------------------------------------------------------
# Schema Constants (module level)
# ------------------------------------------------------------------

REQUIRED_FIELDS = [
    "benchmark_id",
    "question",
    "expected",
    "retrieval",
    "evaluation",
    "metadata",
]

QUESTION_REQUIRED = ["text", "language"]

EXPECTED_REQUIRED = ["gold_tsu_ids", "required_concepts", "expected_scriptures", "expected_doctrine"]

RETRIEVAL_REQUIRED = ["top_k"]

EVALUATION_REQUIRED = ["status"]

METADATA_REQUIRED = ["created_version", "source"]

# JSONL 스키마 예시 (문서용)
SCHEMA_EXAMPLE = {
    "benchmark_id": "B001",
    "question": {
        "text": "예수님이 십자가에서 무엇을 이루셨나요?",
        "language": "ko",
        "question_type": "doctrine",
    },
    "expected": {
        "gold_tsu_ids": ["TSU-0001", "TSU-0042"],
        "required_concepts": ["속죄", "십자가", "대리"],
        "expected_scriptures": ["히브리서 9:22", "로마서 3:25"],
        "expected_doctrine": "대리 속죄설",
    },
    "retrieval": {
        "top_k": 5,
    },
    "evaluation": {
        "status": "pending",
    },
    "metadata": {
        "created_version": "1.0",
        "source": "manual",
        "tsu_schema_version": "",
        "collector_version": "",
        "canonical_version": "",
    },
    "gold_tsu_ids": ["TSU-0001", "TSU-0042"],
    "difficulty": "intermediate",
    "review_status": "draft",
}