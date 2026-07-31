"""NAE Benchmark Schema — Question Unit 정의

자동 정답 생성 금지. 모든 값은 수동 입력 또는 후속 단계에서 생성.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ------------------------------------------------------------------
# Data Classes
# ------------------------------------------------------------------

@dataclass
class BenchmarkQuestion:
    """검색 질문 단위."""

    text: str = ""
    language: str = "ko"  # "ko" | "en"


@dataclass
class BenchmarkExpected:
    """예측 정답 정보 (수동 입력)."""

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


@dataclass
class BenchmarkItem:
    """벤치마크 질문 단위 — 전체 레코드."""

    benchmark_id: str = ""
    question: BenchmarkQuestion = field(default_factory=BenchmarkQuestion)
    expected: BenchmarkExpected = field(default_factory=BenchmarkExpected)
    retrieval: BenchmarkRetrieval = field(default_factory=BenchmarkRetrieval)
    evaluation: BenchmarkEvaluation = field(default_factory=BenchmarkEvaluation)
    metadata: BenchmarkMetadata = field(default_factory=BenchmarkMetadata)

    # retrieved_tsu_ids: 검색 결과로 얻은 TSU ID 목록 (평가 runner에서 채움)
    retrieved_tsu_ids: List[str] = field(default_factory=list)
    retrieved_scores: List[float] = field(default_factory=list)

    # 관련 TSU ID 목록 (gold standard 기준)
    relevant_tsu_ids: List[str] = field(default_factory=list)

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
            "relevant_tsu_ids": self.relevant_tsu_ids,
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
            relevant_tsu_ids=data.get("relevant_tsu_ids", []),
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
            errors.append(f"question.language must be 'ko' or 'en', got '{self.question.language}'")

        if self.retrieval.top_k < 1:
            errors.append("retrieval.top_k must be >= 1")

        return errors


# ------------------------------------------------------------------
# Schema Constants
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

EXPECTED_REQUIRED = ["required_concepts", "expected_scriptures", "expected_doctrine"]

RETRIEVAL_REQUIRED = ["top_k"]

EVALUATION_REQUIRED = ["status"]

METADATA_REQUIRED = ["created_version", "source"]

# JSONL 스키마 예시 (문서용)
SCHEMA_EXAMPLE = {
    "benchmark_id": "B001",
    "question": {
        "text": "예수님이 십자가에서 무엇을 이루셨나요?",
        "language": "ko",
    },
    "expected": {
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
    },
}