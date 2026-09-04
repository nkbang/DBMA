"""NAE/review/human/promotion.py — Promotion Preparation (classification only)
(NAE-PILOT-HUMAN-REVIEW-001 Phase 4).

Classifies validated `HumanReviewResult`s into candidate categories.
**Never writes `review_status`, never calls
`NAE/pipeline/tsu/review_promotion.py::promote_tsu_to_verified()`, never
touches Production TSU files.** Even a `VERIFY` decision only becomes a
"promotion_candidate" here — actual promotion requires a separate,
explicitly-approved task.
"""
from __future__ import annotations

from dataclasses import dataclass

from .schema import HOLD, PILOT_TSU_IDS, REJECT, REVISE, VERIFY, HumanReviewResult

PROMOTION_CANDIDATE = "promotion_candidate"
REVISION_CANDIDATE = "revision_candidate"
REJECTED_CANDIDATE = "rejected_candidate"
PENDING_CANDIDATE = "pending_candidate"

_DECISION_TO_CATEGORY = {
    VERIFY: PROMOTION_CANDIDATE,
    REVISE: REVISION_CANDIDATE,
    REJECT: REJECTED_CANDIDATE,
    HOLD: PENDING_CANDIDATE,
}


@dataclass(frozen=True)
class PromotionCandidate:
    tsu_id: str
    category: str
    decision: str
    reviewer_id: str | None
    revised_claim: str | None = None
    revised_doctrine: str | None = None


@dataclass
class PromotionPreparation:
    candidates: list[PromotionCandidate]
    status: str = "READY_FOR_PROMOTION_REVIEW"

    def by_category(self, category: str) -> list[PromotionCandidate]:
        return [c for c in self.candidates if c.category == category]


def build_promotion_preparation(review_results: list[HumanReviewResult]) -> PromotionPreparation:
    reviewed_ids = {r.tsu_id for r in review_results}
    candidates: list[PromotionCandidate] = []

    for result in review_results:
        candidates.append(
            PromotionCandidate(
                tsu_id=result.tsu_id,
                category=_DECISION_TO_CATEGORY[result.decision],
                decision=result.decision,
                reviewer_id=result.reviewer_id,
                revised_claim=result.revised_claim if result.decision == REVISE else None,
                revised_doctrine=result.revised_doctrine if result.decision == REVISE else None,
            )
        )

    # 아직 Human Review가 도착하지 않은 Pilot TSU는 암묵적으로 PENDING
    # 취급한다(§중요 "Human 결과가 없는 TSU는 PENDING으로 유지").
    for tsu_id in sorted(PILOT_TSU_IDS - reviewed_ids):
        candidates.append(
            PromotionCandidate(tsu_id=tsu_id, category=PENDING_CANDIDATE, decision="PENDING", reviewer_id=None)
        )

    return PromotionPreparation(candidates=candidates)
