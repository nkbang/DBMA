"""scripts/crosswalk/schema.py — Crosswalk Record 데이터 구조
(NAE-CROSSWALK-ADAPTER-IMPLEMENTATION-001).

`docs/NAE_IDENTIFIER_CROSSWALK_SCHEMA_001.md`(C1 Approved)의 10개
필드를 저장 위치와 무관한 순수 dataclass로 구현한다 — YAML 파일이든,
Manifest 확장 필드든, DB row든 어디서 왔든 이 dataclass로 표현할 수
있어야 한다(ADR-019 Storage Decision 조건부 보류 상태 유지).

이 모듈은 **구조적 유효성**(필수 필드 존재, enum 값이 정의된 범위
안에 있는지)만 검증한다. **정책 유효성**(evidence 필수 여부, 중복
여부 등, Mapping Policy Rule 1-3)은 이 모듈이 아니라
`scripts/crosswalk/validator.py`가 배치 단위로 검사한다 — 하나의
잘못된 레코드 때문에 전체 배치 검증이 예외로 중단되지 않도록
의도적으로 분리했다.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class SchemaError(ValueError):
    """구조적으로 유효하지 않은 Crosswalk Record(필수 필드 누락, enum 값 오류)."""


class SourceType(str, Enum):
    REGISTRY_SOURCE_ID = "registry_source_id"


class TargetType(str, Enum):
    CORPUS_CANONICAL_ID = "corpus_canonical_id"
    CORPUS_RAW_ID = "corpus_raw_id"


class MappingStatus(str, Enum):
    VERIFIED = "verified"
    EVIDENCE_BACKED = "evidence-backed"
    MANUAL_CONFIRMED = "manual-confirmed"
    UNMAPPED = "unmapped"


class Confidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# Rule 2(Confidence Gate)의 "confidence < 1.0 → unresolved" 요구사항을
# enum 기반 confidence(Schema Design 001, C1 Approved)와 양립시키기
# 위한 수치 매핑 — 스키마 필드 타입 자체는 바꾸지 않는다(승인된 설계
# 유지), Gate 판정에서만 이 점수를 사용한다.
CONFIDENCE_SCORE: dict[Confidence, float] = {
    Confidence.HIGH: 1.0,
    Confidence.MEDIUM: 0.66,
    Confidence.LOW: 0.33,
}


def confidence_score(confidence: Confidence | None) -> float:
    if confidence is None:
        return 0.0
    return CONFIDENCE_SCORE[Confidence(confidence)]


# Gate(Rule 1 + Rule 2)를 통과할 수 있는 mapping_status 집합 — 이 밖의
# 값(evidence-backed, unmapped 포함)은 구조적으로는 유효한 Crosswalk
# Record일 수 있으나, TSU Pipeline에 넘길 만큼 확정된 상태는 아니다.
GATE_ELIGIBLE_STATUSES: frozenset[MappingStatus] = frozenset(
    {MappingStatus.VERIFIED, MappingStatus.MANUAL_CONFIRMED}
)


@dataclass(frozen=True)
class CrosswalkRecord:
    """불변(frozen) 레코드 — 한 번 생성된 Crosswalk Record의 식별자/매핑
    값은 이후 그 자리에서 수정할 수 없다("immutable identifier 유지",
    NAE-CROSSWALK-TEST-EVIDENCE-FIX-001 T2). 값을 바꾸려면 새 레코드를
    만들어야 한다 — Migration Engine Audit Log의 append-only 원칙과
    동일 정신."""

    crosswalk_id: str
    source_identifier: str
    source_type: SourceType
    target_identifier: str
    target_type: TargetType
    mapping_status: MappingStatus
    confidence: Confidence | None
    evidence: str | None
    created_at: str
    verified_at: str | None = None

    def __post_init__(self) -> None:
        for field_name in ("crosswalk_id", "source_identifier", "target_identifier", "created_at"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise SchemaError(f"{field_name} 누락 또는 빈 문자열: {value!r}")

        # frozen dataclass이므로 일반 대입 대신 object.__setattr__ 사용
        # (생성 시점 1회 정규화만 허용, 이후에는 __post_init__ 자체가
        # 다시 호출되지 않으므로 불변성이 깨지지 않는다).
        object.__setattr__(self, "source_type", SourceType(self.source_type))
        object.__setattr__(self, "target_type", TargetType(self.target_type))
        object.__setattr__(self, "mapping_status", MappingStatus(self.mapping_status))
        if self.confidence is not None:
            object.__setattr__(self, "confidence", Confidence(self.confidence))

    def to_dict(self) -> dict[str, Any]:
        return {
            "crosswalk_id": self.crosswalk_id,
            "source_identifier": self.source_identifier,
            "source_type": self.source_type.value,
            "target_identifier": self.target_identifier,
            "target_type": self.target_type.value,
            "mapping_status": self.mapping_status.value,
            "confidence": self.confidence.value if self.confidence else None,
            "evidence": self.evidence,
            "created_at": self.created_at,
            "verified_at": self.verified_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CrosswalkRecord":
        try:
            return cls(
                crosswalk_id=data["crosswalk_id"],
                source_identifier=data["source_identifier"],
                source_type=data["source_type"],
                target_identifier=data["target_identifier"],
                target_type=data["target_type"],
                mapping_status=data["mapping_status"],
                confidence=data.get("confidence"),
                evidence=data.get("evidence"),
                created_at=data["created_at"],
                verified_at=data.get("verified_at"),
            )
        except KeyError as exc:
            raise SchemaError(f"필수 필드 누락: {exc}") from exc

    def is_gate_eligible(self) -> bool:
        """Resolver/TSU Gate가 이 레코드를 신뢰해 사용할 수 있는가 —
        Rule 1(manual-confirmed/verified만) + Rule 2(confidence < 1.0 이면
        unresolved, 즉 confidence_score == 1.0(HIGH)만 통과) + Rule 3
        (evidence 필수)을 전부 만족해야 한다.
        """
        if self.mapping_status not in GATE_ELIGIBLE_STATUSES:
            return False
        if confidence_score(self.confidence) < 1.0:
            return False
        if not self.evidence or not self.evidence.strip():
            return False
        return True
