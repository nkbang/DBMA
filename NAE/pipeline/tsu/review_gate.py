"""NAE/pipeline/tsu/review_gate.py — TSU Review Gate
(NAE-TSU-REVIEW-GATE-IMPLEMENTATION-001).

Blocks TSU records whose `review_status` is not `"verified"` from
reaching the Embedding/Vector Index stage. Pure judgment module — no
side effects: does not write TSU files, does not call the embedding
client (`NAE/pipeline/embed/`), does not touch Qdrant
(`NAE/pipeline/index/qdrant_store.py`), does not generate TSU
(`builder.py` is not imported here).

**Naming collision warning (discovered during Phase 1 audit)**:
`NAE/pipeline/index/indexer.py` already has a file named
`tsu_verified.json` (Phase 3.5 duplicate-detection output — "verified"
there means "de-duplication pass has run", carries `score`/
`duplicate_of` fields). That is a *different* concept from this
module's `review_status == "verified"` (human claim-quality review).
This module does not read or write `tsu_verified.json` — the two
"verified" concepts are not reconciled by this task (see the
implementation report's WARNING/NEXT STEP).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

# Phase 2 — Review Status Contract
GENERATED = "generated"
REVIEWED = "reviewed"
VERIFIED = "verified"
REJECTED = "rejected"

VALID_REVIEW_STATUSES: frozenset[str] = frozenset({GENERATED, REVIEWED, VERIFIED, REJECTED})
EMBEDDING_ELIGIBLE_STATUSES: frozenset[str] = frozenset({VERIFIED})


class ReviewGateStatus(str, Enum):
    PASS = "REVIEW_GATE_PASS"
    BLOCK = "REVIEW_GATE_BLOCK"


@dataclass
class ReviewGateResult:
    status: ReviewGateStatus
    reason: str
    tsu_id: str | None
    review_status: str | None

    @property
    def eligible(self) -> bool:
        return self.status == ReviewGateStatus.PASS


def check_tsu_review_status(tsu_record: dict[str, Any] | None) -> ReviewGateResult:
    """단일 TSU 레코드(dict, `NAE/pipeline/tsu/builder.py`가 `tsu.json`에
    쓰는 것과 동일 형태)를 판정한다.

    잘못된/알 수 없는 `review_status` 값은 별도 ERROR 상태를 두지 않고
    BLOCK으로 처리한다(설계 결정 — Embedding 대상 여부만 판정하는 이
    Gate 입장에서는 "verified가 아니면 전부 통과 불가"라는 단일 원칙이
    "잘못된 값"과 "아직 검토 전"을 구태여 구분할 필요를 없앤다 — 구분이
    필요해지면 Crosswalk TSU Gate의 ERROR 패턴을 재사용해 확장 가능).
    """
    if not tsu_record:
        return ReviewGateResult(ReviewGateStatus.BLOCK, "empty TSU record", None, None)

    tsu_id = tsu_record.get("id")
    review_status = tsu_record.get("review_status")

    if review_status is None:
        return ReviewGateResult(ReviewGateStatus.BLOCK, "review_status missing", tsu_id, None)

    if review_status not in VALID_REVIEW_STATUSES:
        return ReviewGateResult(
            ReviewGateStatus.BLOCK, f"invalid review_status={review_status!r}", tsu_id, review_status
        )

    if review_status not in EMBEDDING_ELIGIBLE_STATUSES:
        return ReviewGateResult(
            ReviewGateStatus.BLOCK,
            f"review_status={review_status!r} not eligible for embedding (requires 'verified')",
            tsu_id,
            review_status,
        )

    return ReviewGateResult(ReviewGateStatus.PASS, "review_status=verified", tsu_id, review_status)


@dataclass
class ReviewGateBatchSummary:
    total: int = 0
    pass_count: int = 0
    block_count: int = 0
    pass_records: list[dict[str, Any]] = field(default_factory=list)
    block_details: list[tuple[str | None, str]] = field(default_factory=list)


def filter_embedding_eligible(tsu_records: list[dict[str, Any]]) -> ReviewGateBatchSummary:
    """여러 TSU 레코드를 한 번에 판정한다(Phase 3 "multiple TSU batch
    처리" 요구사항) — `verified`인 것만 `pass_records`에 담아 반환,
    나머지는 `block_details`에 사유와 함께 기록한다."""
    summary = ReviewGateBatchSummary(total=len(tsu_records))
    for record in tsu_records:
        result = check_tsu_review_status(record)
        if result.status == ReviewGateStatus.PASS:
            summary.pass_count += 1
            summary.pass_records.append(record)
        else:
            summary.block_count += 1
            summary.block_details.append((result.tsu_id, result.reason))
    return summary


def load_embedding_eligible_records(identifier: str, tsu_root: Path) -> tuple[list[dict[str, Any]], ReviewGateBatchSummary]:
    """Phase 4 — Vector Pipeline 보호 Interface.

    `tsu_root/identifier/tsu.json`을 읽어 Gate를 통과한(`verified`)
    레코드만 반환한다. **이 함수는 아직 `NAE/pipeline/index/indexer.py`
    에 배선되지 않았다** — 그 모듈의 `load_records()`를 대체하려면
    별도 Wiring 작업이 필요하다(구현 보고서 WARNING/NEXT STEP 참고).
    이 함수 자체는 읽기 전용이며, embedding 호출이나 Qdrant 접근을
    전혀 하지 않는다.
    """
    path = tsu_root / identifier / "tsu.json"
    if not path.exists():
        return [], ReviewGateBatchSummary(total=0)
    records = json.loads(path.read_text(encoding="utf-8"))
    summary = filter_embedding_eligible(records)
    return summary.pass_records, summary
