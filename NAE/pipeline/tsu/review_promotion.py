"""NAE/pipeline/tsu/review_promotion.py — TSU Review Promotion
(NAE-TSU-REVIEW-WORKFLOW-IMPLEMENTATION-001).

Implements `docs/NAE_TSU_REVIEW_WORKFLOW_DESIGN_001.md` Phase 2/3 —
the only path by which a TSU record's `review_status` may become
`"verified"`. Pure function, no side effects: never writes files,
never touches the embedding client or Qdrant, never mutates its input
in place (always returns a new dict, mirroring the immutable-record
principle already used by `scripts/crosswalk/schema.py::CrosswalkRecord`).

**Naming disambiguation (carried over from the Design doc)**:
`tsu_verified.json` (`NAE/pipeline/verify/duplicate.py`, Phase 3.5) is
a dedup/generation validation artifact — it means "near-duplicate
detection has run", nothing more. `review_status == "verified"` (this
module) means a human has completed theological review. This module
never reads or writes `tsu_verified.json`; the two concepts are not
conflated anywhere in this file.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

APPROVED = "approved"
REJECTED = "rejected"
VALID_DECISIONS: frozenset[str] = frozenset({APPROVED, REJECTED})


class PromotionStatus(str, Enum):
    PASS = "PROMOTION_PASS"
    BLOCK = "PROMOTION_BLOCK"


@dataclass
class PromotionResult:
    status: PromotionStatus
    reason: str
    tsu_id: str | None
    record: dict[str, Any] | None
    """성공(PASS) 또는 review_decision=rejected 처리 시에만 채워지는
    *새* 레코드(원본 dict는 절대 in-place 수정하지 않음). 그 외 BLOCK
    사유(reviewer/review_date/review_decision 누락 등)에서는 None —
    "verified로 바뀐 레코드가 존재하지 않는다"는 것을 명확히 한다."""

    @property
    def promoted(self) -> bool:
        return self.status == PromotionStatus.PASS


def _build_review_metadata(
    reviewer: str, review_date: str, review_decision: str, review_notes: str | None
) -> dict[str, Any]:
    return {
        "reviewer": reviewer,
        "review_date": review_date,
        "review_decision": review_decision,
        "review_notes": review_notes,
    }


def promote_tsu_to_verified(
    tsu_record: dict[str, Any] | None,
    *,
    reviewer: str | None,
    review_date: str | None,
    review_decision: str | None,
    review_notes: str | None = None,
) -> PromotionResult:
    """`review_status`를 `"verified"`로 승격을 시도한다.

    ALL REQUIRED(하나라도 없으면 BLOCK, 자동/강제/기본값 승격 없음):
        reviewer != empty
        review_date != empty
        review_decision == "approved"

    기존 TSU claim 필드(`claim`/`doctrine`/`scriptures`/`citations`/
    `confidence`/`extraction_method`/`model`)와 `id`는 절대 건드리지
    않는다 — `review_status`와 `review_metadata` 2개 필드만 추가/갱신한
    새 dict를 반환한다.
    """
    tsu_id = tsu_record.get("id") if tsu_record else None

    if not tsu_record:
        return PromotionResult(PromotionStatus.BLOCK, "empty TSU record", tsu_id, None)

    if not reviewer or not isinstance(reviewer, str) or not reviewer.strip():
        return PromotionResult(PromotionStatus.BLOCK, "reviewer missing", tsu_id, None)

    if not review_date or not isinstance(review_date, str) or not review_date.strip():
        return PromotionResult(PromotionStatus.BLOCK, "review_date missing", tsu_id, None)

    if review_decision not in VALID_DECISIONS:
        return PromotionResult(
            PromotionStatus.BLOCK, f"invalid review_decision={review_decision!r}", tsu_id, None
        )

    review_metadata = _build_review_metadata(reviewer, review_date, review_decision, review_notes)

    if review_decision == REJECTED:
        new_record = dict(tsu_record)
        new_record["review_status"] = "rejected"
        new_record["review_metadata"] = review_metadata
        return PromotionResult(PromotionStatus.BLOCK, "review_decision=rejected", tsu_id, new_record)

    # review_decision == "approved"부터는 verified 승격 후보
    if tsu_record.get("review_status") == "verified":
        # 이미 verified인 레코드의 재승격 요청 — 멱등 처리: 기존 레코드를
        # 그대로 반환(덮어쓰지 않음)하고 PASS로 응답한다. 재검토 이력이
        # 필요하면 새 TSU 레코드를 만드는 것이 원칙(설계 문서 §Phase2
        # "verified -> 역행은 다루지 않는다, 재검토는 새 레코드로").
        return PromotionResult(
            PromotionStatus.PASS, "already verified (idempotent, not re-promoted)", tsu_id, dict(tsu_record)
        )

    new_record = dict(tsu_record)
    new_record["review_status"] = "verified"
    new_record["review_metadata"] = review_metadata
    return PromotionResult(PromotionStatus.PASS, "promoted to verified", tsu_id, new_record)


def promote_batch(
    tsu_records: list[dict[str, Any]],
    *,
    reviewer: str | None,
    review_date: str | None,
    review_decision: str | None,
    review_notes: str | None = None,
) -> list[PromotionResult]:
    """여러 TSU 레코드에 동일한 검토 메타데이터를 일괄 적용한다(Phase 5
    "batch promotion" 요구사항). 레코드마다 독립적으로 판정되며, 하나가
    실패해도 나머지는 계속 처리한다."""
    return [
        promote_tsu_to_verified(
            record,
            reviewer=reviewer,
            review_date=review_date,
            review_decision=review_decision,
            review_notes=review_notes,
        )
        for record in tsu_records
    ]
