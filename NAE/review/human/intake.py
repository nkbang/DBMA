"""NAE/review/human/intake.py — Human Review Result Intake
(NAE-PILOT-HUMAN-REVIEW-001 Phase 1/2).

Parses and validates Human Reviewer input (JSONL, one record per line)
against the schema in `schema.py`. Never writes to Production TSU files,
never touches `review_status`, never invents a reviewer's decision.
"""
from __future__ import annotations

import json
from pathlib import Path

from .schema import HOLD, PILOT_TSU_IDS, REJECT, REVISE, VALID_DECISIONS, VERIFY, HumanReviewResult

DEFAULT_RESULTS_PATH = Path("NAE/review/human/pilot_001_review_results.jsonl")

# 호환 별칭(다른 세션이 __init__.py에서 이 이름들로 import하도록 남긴
# 것을 그대로 존중 — 되돌리지 않고 실제 구현에 연결만 한다).
ReviewResult = HumanReviewResult
ALLOWED_DECISIONS = VALID_DECISIONS
PENDING_STATUS = "PENDING_HUMAN_REVIEW"


class IntakeError(ValueError):
    """Reviewer 입력이 구조적으로 유효하지 않음(§Phase2 ERROR 항목)."""


def validate_review_result(entry: dict) -> HumanReviewResult:
    tsu_id = entry.get("tsu_id")
    if not tsu_id or not isinstance(tsu_id, str):
        raise IntakeError("missing tsu_id")
    if tsu_id not in PILOT_TSU_IDS:
        raise IntakeError(f"tsu_id not in Pilot 10건: {tsu_id!r}")

    reviewer_id = entry.get("reviewer_id")
    if not reviewer_id or not isinstance(reviewer_id, str):
        raise IntakeError(f"{tsu_id}: missing reviewer_id")

    review_timestamp = entry.get("review_timestamp")
    if not review_timestamp or not isinstance(review_timestamp, str):
        raise IntakeError(f"{tsu_id}: missing review_timestamp")

    decision = entry.get("decision")
    if not decision:
        raise IntakeError(f"{tsu_id}: missing decision")
    if decision not in VALID_DECISIONS:
        raise IntakeError(f"{tsu_id}: invalid decision {decision!r} (allowed: {sorted(VALID_DECISIONS)})")

    revised_claim = entry.get("revised_claim")
    revised_doctrine = entry.get("revised_doctrine")

    if decision == REVISE and not revised_claim:
        raise IntakeError(f"{tsu_id}: REVISE decision requires revised_claim")

    if decision in (REJECT, HOLD) and (revised_claim or revised_doctrine):
        raise IntakeError(
            f"{tsu_id}: {decision} decision must not carry revised_claim/revised_doctrine "
            "(promotion-only fields, reserved for REVISE)"
        )

    return HumanReviewResult(
        tsu_id=tsu_id,
        reviewer_id=reviewer_id,
        review_timestamp=review_timestamp,
        decision=decision,
        claim_fidelity=entry.get("claim_fidelity"),
        theological_accuracy=entry.get("theological_accuracy"),
        doctrine_classification=entry.get("doctrine_classification"),
        evidence_sufficiency=entry.get("evidence_sufficiency"),
        scripture_citation_assessment=entry.get("scripture_citation_assessment"),
        reviewer_notes=entry.get("reviewer_notes"),
        revised_claim=revised_claim,
        revised_doctrine=revised_doctrine,
        context_required=bool(entry.get("context_required", False)),
        source_verification_required=bool(entry.get("source_verification_required", False)),
    )


def _read_entries(path: Path) -> list[dict]:
    """`pilot_001_review_results.jsonl`은 컨테이너 JSON 객체 1개
    (`{"reviews": [...], ...}`) 형식이다 — 각 원소가 1건의 Reviewer
    입력이다. 과거 순수 JSONL(줄마다 JSON 1개)로 작성된 파일도 하위
    호환으로 계속 읽는다."""
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, dict):
        # 컨테이너 형식 — "reviews" 키가 아예 없으면(헤더만 있는 초기
        # 상태) 아직 아무도 검토하지 않은 것으로 취급한다(에러 아님).
        reviews = parsed.get("reviews", [])
        if reviews is None:
            reviews = []
        if not isinstance(reviews, list):
            raise IntakeError("'reviews' 필드는 리스트여야 함")
        return reviews
    if isinstance(parsed, list):
        return parsed
    # JSONL(줄 단위) 형식 fallback
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def load_review_results(path: Path = DEFAULT_RESULTS_PATH) -> tuple[list[HumanReviewResult], list[str]]:
    """Review Result 컨테이너 파일을 읽어 검증된 `HumanReviewResult`
    목록과 duplicate 처리 노트를 반환한다. 파일이 없거나 `reviews`가
    비어있으면(=아직 아무도 검토하지 않음) 빈 목록을 반환 — 이것이
    정상 상태다(§중요 "Human 결과가 없는 TSU는 PENDING으로 유지").

    동일 tsu_id에 완전히 동일한 내용이 여러 건 있으면 duplicate(멱등,
    에러 아님)로 처리하고 한 건만 채택한다. 동일 tsu_id에 서로 다른
    reviewer_id/decision이 있으면 conflicting review로 간주해
    `IntakeError`를 발생시킨다 — 자동으로 하나를 고르지 않는다."""
    if not path.exists():
        return [], []

    entries = _read_entries(path)
    grouped: dict[str, list[HumanReviewResult]] = {}
    for entry in entries:
        result = validate_review_result(entry)
        grouped.setdefault(result.tsu_id, []).append(result)

    results: list[HumanReviewResult] = []
    duplicate_notes: list[str] = []
    for tsu_id, entries in grouped.items():
        if len(entries) == 1:
            results.append(entries[0])
            continue
        first_dict = entries[0].to_dict()
        if all(e.to_dict() == first_dict for e in entries[1:]):
            duplicate_notes.append(f"{tsu_id}: {len(entries)}건 동일 입력 중복 제출, 1건만 채택")
            results.append(entries[0])
        else:
            raise IntakeError(
                f"{tsu_id}: conflicting reviews from multiple submissions "
                f"({[e.reviewer_id for e in entries]}) — 자동 해결 금지, 사람 재확인 필요"
            )
    return results, duplicate_notes


class ReviewIntake:
    """`validate_review_result()`/`load_review_results()`의 얇은 클래스
    래퍼 — 동작은 동일하고 편의상 인스턴스 API만 제공한다."""

    def __init__(self, path: Path = DEFAULT_RESULTS_PATH) -> None:
        self.path = path

    def validate(self, entry: dict) -> HumanReviewResult:
        return validate_review_result(entry)

    def load(self) -> tuple[list[HumanReviewResult], list[str]]:
        return load_review_results(self.path)
