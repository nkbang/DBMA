"""scripts/corpus_approval_gate.py — Corpus Mutation Approval Gate

NAE Default Corpus에 대한 실제 mutation을 승인된 source로만 제한하는
safety boundary. 기존 `NAE/review/human/decision_gate.py`의
`HumanDecisionRecord` / `is_promotion_eligible()` / `decisions/*.json`
구조를 재사용하여 중복 approval system을 만들지 않는다.

Policy:
    1. 기본 실행은 mutation을 허용하지 않는다.
    2. 승인되지 않은 source는 mutation할 수 없다.
    3. 승인 목록에 없는 source는 명시적으로 거부한다.
    4. 승인 정보가 없거나 불완전하면 fail-closed 한다.
    5. 단순 CLI 실행만으로 production corpus가 변경되어서는 안 된다.

Approval model (기존 convention 우선):
    APPROVED  = "APPROVED"   (HumanDecisionRecord.final_decision)
    REJECTED  = "REJECTED"
    CONDITIONAL = "CONDITIONAL"
    NOT_APPROVED = "NOT_APPROVED"  (record 없음 / incomplete)

Gate location:
    `verify_corpus_mutation_approval()` — merge() 호출 전 반드시 통과.
    이 함수가 True를 반환하지 않으면 mutation code에 도달할 수 없다.

Usage:
    from scripts.corpus_approval_gate import (
        verify_corpus_mutation_approval,
        CorpusMutationApprovalResult,
    )

    result = verify_corpus_mutation_approval(
        source_id="Fuller_Complete_Works_Vol02",
        decisions_dir=Path("NAE/review/human/decisions"),
        tsu_ids={"TSU-0007768", "TSU-0007769"},
    )
    if not result.approved:
        raise CorpusMutationBlockedError(result.reason)
    # ... proceed with mutation
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Enums / Constants
# ---------------------------------------------------------------------------

class ApprovalStatus(str, Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CONDITIONAL = "CONDITIONAL"
    NOT_APPROVED = "NOT_APPROVED"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CorpusMutationApprovalResult:
    """Corpus mutation 승인 판정 결과."""
    source_id: str
    status: ApprovalStatus
    approved_tsu_ids: frozenset[str] = field(default_factory=frozenset)
    rejected_tsu_ids: frozenset[str] = field(default_factory=frozenset)
    reason: str = ""

    @property
    def approved(self) -> bool:
        return self.status == ApprovalStatus.APPROVED

    @property
    def blocked(self) -> bool:
        return not self.approved


@dataclass(frozen=True)
class CorpusMutationManifest:
    """승인된 source의 corpus mutation manifest.

    merge plan이 이 manifest와 정확히 일치해야 한다.
    """
    source_id: str
    approved_tsu_ids: frozenset[str]
    approved_count: int
    reviewer_id: str
    review_timestamp: str | None
    final_decision: str  # "APPROVED" / "CONDITIONAL"


# ---------------------------------------------------------------------------
# Core gate functions
# ---------------------------------------------------------------------------

def _load_decisions(decisions_dir: Path) -> list[dict[str, Any]]:
    """decisions_dir의 모든 .json 파일을 읽어 decisions 목록을 반환.

    **기존 `decision_gate.py`의 `_validate_decision_entry()`를 재사용**하여
    필수 metadata(gate_id/tsu_id/reviewer_id/answers) 검증한다.
    validation 실패 시 해당 entry를 건너뛰지 않고 즉시 BLOCK한다.
    """
    if not decisions_dir.exists():
        return []
    records: list[dict[str, Any]] = []
    for path in sorted(decisions_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        entries = data.get("decisions", data if isinstance(data, list) else [data])
        for entry in entries:
            # 필수 metadata 검증 — 기존 decision_gate.py convention 재사용
            gate_id = entry.get("gate_id")
            tsu_id = entry.get("tsu_id")
            reviewer_id = entry.get("reviewer_id")
            answers = entry.get("answers")
            if not gate_id or not tsu_id:
                # gate_id/tsu_id 누락 → fail-closed: 해당 entry를 건너뛰지 않고
                # caller가 BLOCK하도록 빈 목록을 반환하여 전체 차단
                return []
            if not reviewer_id:
                return []
            if not answers or not isinstance(answers, dict):
                return []
            records.append(entry)
    return records


def _find_source_decisions(
    decisions: list[dict[str, Any]], source_id: str
) -> list[dict[str, Any]]:
    """source_id에 해당하는 decision entries만 필터."""
    return [
        d for d in decisions
        if d.get("work_id") == source_id or d.get("edition_id") == source_id
           or d.get("identifier") == source_id
           or d.get("source_id") == source_id
    ]


def verify_corpus_mutation_approval(
    source_id: str,
    decisions_dir: Path,
    tsu_ids: Optional[frozenset[str]] = None,
) -> CorpusMutationApprovalResult:
    """Corpus mutation 승인 여부를 판정한다.

    이 함수가 approved=False를 반환하면 mutation을 절대 수행해서는 안 된다.

    Args:
        source_id: mutation 대상 source 식별자 (work_id / edition_id).
        decisions_dir: HumanDecisionRecord 파일이 있는 디렉터리.
        tsu_ids: mutation 대상 TSU ID 집합 (선택적 — manifest 일치 검증용).

    Returns:
        CorpusMutationApprovalResult — 승인 상태와 상세 정보.
    """
    decisions = _load_decisions(decisions_dir)

    if not decisions:
        return CorpusMutationApprovalResult(
            source_id=source_id,
            status=ApprovalStatus.NOT_APPROVED,
            reason="decisions directory is empty or does not exist — fail-closed",
        )

    source_decisions = _find_source_decisions(decisions, source_id)

    if not source_decisions:
        return CorpusMutationApprovalResult(
            source_id=source_id,
            status=ApprovalStatus.NOT_APPROVED,
            reason=f"No decision records found for source_id={source_id!r}",
        )

    # 판정 집계: 모든 decision entry의 final_decision을 확인
    approved_ids: list[str] = []
    rejected_ids: list[str] = []
    conditional_ids: list[str] = []

    for entry in source_decisions:
        tsu_id = entry.get("tsu_id", "")
        final_decision = entry.get("final_decision")

        if final_decision == "APPROVED":
            approved_ids.append(tsu_id)
        elif final_decision == "REJECTED":
            rejected_ids.append(tsu_id)
        elif final_decision == "CONDITIONAL":
            conditional_ids.append(tsu_id)
        else:
            # final_decision이 없거나 알 수 없는 값 — 해당 TSU는 승인되지 않음
            if tsu_id:
                rejected_ids.append(tsu_id)

    # CONDITIONAL이 하나라도 있으면 반드시 BLOCK (핵심 invariant)
    if conditional_ids:
        return CorpusMutationApprovalResult(
            source_id=source_id,
            status=ApprovalStatus.NOT_APPROVED,
            approved_tsu_ids=frozenset(approved_ids),
            rejected_tsu_ids=frozenset(rejected_ids + conditional_ids),
            reason=(
                f"CONDITIONAL TSU(s) found — mutation blocked: "
                f"{len(conditional_ids)} CONDITIONAL, {len(approved_ids)} APPROVED, "
                f"{len(rejected_ids)} REJECTED. "
                "All TSUs must be APPROVED for mutation."
            ),
        )

    # 전체 source가 APPROVED여야 mutation 허용
    if not approved_ids:
        return CorpusMutationApprovalResult(
            source_id=source_id,
            status=ApprovalStatus.NOT_APPROVED,
            reason="No TSU records have final_decision=APPROVED for this source",
            rejected_tsu_ids=frozenset(rejected_ids),
        )

    if rejected_ids:
        return CorpusMutationApprovalResult(
            source_id=source_id,
            status=ApprovalStatus.NOT_APPROVED,
            approved_tsu_ids=frozenset(approved_ids),
            rejected_tsu_ids=frozenset(rejected_ids),
            reason=(
                f"REJECTED TSU(s) found — mutation blocked: "
                f"{len(rejected_ids)} REJECTED, {len(approved_ids)} APPROVED. "
                "All TSUs must be APPROVED for mutation."
            ),
        )

    # 전체 승인 (CONDITIONAL + REJECTED 없음 확인됨)
    result = CorpusMutationApprovalResult(
        source_id=source_id,
        status=ApprovalStatus.APPROVED,
        approved_tsu_ids=frozenset(approved_ids),
        reason="All TSU records for this source are APPROVED",
    )

    # 선택적: tsu_ids가 제공되면 manifest 일치 검증
    if tsu_ids is not None and result.approved:
        if not tsu_ids.issubset(result.approved_tsu_ids):
            unapproved = tsu_ids - result.approved_tsu_ids
            return CorpusMutationApprovalResult(
                source_id=source_id,
                status=ApprovalStatus.NOT_APPROVED,
                reason=(
                    f"Manifest mismatch: {len(unapproved)} TSU(s) not in approved set. "
                    f"Requested: {sorted(unapproved)[:5]}... (showing first 5)"
                ),
                approved_tsu_ids=result.approved_tsu_ids,
            )

    return result


def build_approval_manifest(
    source_id: str,
    decisions_dir: Path,
) -> CorpusMutationManifest | None:
    """source_id에 대한 승인 manifest를 구축한다.

    승인되지 않은 source는 None을 반환 (fail-closed).
    """
    result = verify_corpus_mutation_approval(source_id, decisions_dir)
    if not result.approved:
        return None

    # reviewer_id / timestamp 수집
    decisions = _load_decisions(decisions_dir)
    source_decisions = _find_source_decisions(decisions, source_id)
    reviewer_ids = set()
    timestamps = []
    for entry in source_decisions:
        if entry.get("final_decision") == "APPROVED":
            if entry.get("reviewer_id"):
                reviewer_ids.add(entry["reviewer_id"])
            if entry.get("review_timestamp"):
                timestamps.append(entry["review_timestamp"])

    # reviewer_id 필수 — 기존 decision_gate.py convention에 따라
    # missing reviewer_id → manifest build 실패 (fail-closed)
    if not reviewer_ids:
        return None

    return CorpusMutationManifest(
        source_id=source_id,
        approved_tsu_ids=result.approved_tsu_ids,
        approved_count=len(result.approved_tsu_ids),
        reviewer_id=", ".join(sorted(reviewer_ids)),
        review_timestamp=max(timestamps) if timestamps else None,
        final_decision="APPROVED",
    )


def validate_merge_plan_against_manifest(
    manifest: CorpusMutationManifest,
    planned_tsu_ids: frozenset[str],
) -> tuple[bool, str]:
    """merge plan이 manifest와 정확히 일치하는지 검증.

    Returns:
        (is_valid, reason) — is_valid=True일 때만 merge 가능.
    """
    if not manifest.approved_tsu_ids:
        return False, "Manifest has no approved TSU IDs"

    if planned_tsu_ids != manifest.approved_tsu_ids:
        extra = planned_tsu_ids - manifest.approved_tsu_ids
        missing = manifest.approved_tsu_ids - planned_tsu_ids
        parts = []
        if extra:
            parts.append(f"extra={sorted(extra)[:5]}...")
        if missing:
            parts.append(f"missing={sorted(missing)[:5]}...")
        return False, f"Plan-manifest mismatch: {'; '.join(parts)}"

    return True, "Plan matches manifest exactly"


class CorpusMutationBlockedError(Exception):
    """승인되지 않은 corpus mutation이 시도될 때 발생."""
    pass

