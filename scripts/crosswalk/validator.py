"""scripts/crosswalk/validator.py — Crosswalk Mapping Policy Validator
(NAE-CROSSWALK-ADAPTER-IMPLEMENTATION-001).

`docs/NAE_IDENTIFIER_CROSSWALK_MAPPING_POLICY_001.md`(C1 Approved)의
Rule 1(추측 매핑 금지)/Rule 2(Confidence Gate)/Rule 3(Evidence 필수)를
배치 단위로 검사한다. 기존 3-Validator(source/manifest/authority)는
이 모듈에서 전혀 import하지 않는다 — 완전히 독립된 신규 Validator다
(작업 명령서 §6 "기존 Validator 변경 금지").
"""

from __future__ import annotations

from collections import Counter

from .schema import CrosswalkRecord, MappingStatus, confidence_score


class ValidationResult:
    def __init__(self) -> None:
        self.pass_count = 0
        self.warning_count = 0
        self.fail_count = 0
        self.lines: list[str] = []

    def add(self, level: str, message: str) -> None:
        level = level.upper()
        if level == "PASS":
            self.pass_count += 1
        elif level == "WARNING":
            self.warning_count += 1
        elif level == "FAIL":
            self.fail_count += 1
        self.lines.append(f"[{level}] {message}")

    def print_all(self) -> None:
        for line in self.lines:
            print(line)
        print()
        print(f"=== Crosswalk 검증 결과: PASS={self.pass_count} WARNING={self.warning_count} FAIL={self.fail_count} ===")


# mapping_status 값 중 Rule 1이 명시적으로 금지하는 예시(작업 명령서
# §4 Rule 1) — CrosswalkRecord.mapping_status는 이미 schema.py의
# MappingStatus enum으로 강제되므로 이 값들은 애초에 구조적으로
# 생성 불가능하지만(Check 4가 잡음), 문서화 목적으로 명시해 둔다.
_EXPLICITLY_FORBIDDEN_STATUS_STRINGS = frozenset({"auto-guessed", "inferred", "unknown-match"})

# evidence가 필수인 mapping_status(unmapped만 예외)
_EVIDENCE_REQUIRED_STATUSES = frozenset(
    {MappingStatus.VERIFIED, MappingStatus.EVIDENCE_BACKED, MappingStatus.MANUAL_CONFIRMED}
)


def validate(
    records: list[CrosswalkRecord],
    valid_source_identifiers: set[str] | None = None,
) -> ValidationResult:
    """Crosswalk Record 목록을 5개 항목으로 검사한다.

    valid_source_identifiers가 주어지면 Check 5(Broken identifier
    reference)에서 Registry/Manifest의 실제 source_id 집합과 대조한다
    — 주어지지 않으면 Check 5는 건너뛴다(PASS 처리, 대조 대상 없음을
    WARNING으로 표시).
    """
    result = ValidationResult()

    if not records:
        result.add("WARNING", "검증할 Crosswalk Record 없음")
        return result

    _check_duplicate_crosswalk_id(records, result)
    _check_duplicate_source_target_pair(records, result)
    _check_missing_evidence(records, result)
    _check_invalid_mapping_status(records, result)
    _check_broken_identifier_reference(records, result, valid_source_identifiers)

    return result


def _check_duplicate_crosswalk_id(records: list[CrosswalkRecord], result: ValidationResult) -> None:
    """Check 1 — Duplicate crosswalk_id."""
    counts = Counter(r.crosswalk_id for r in records)
    for record in records:
        if counts[record.crosswalk_id] > 1:
            result.add("FAIL", f"crosswalk_id 중복: {record.crosswalk_id!r}")
        else:
            result.add("PASS", f"crosswalk_id={record.crosswalk_id!r} 유일성 확인")


def _check_duplicate_source_target_pair(records: list[CrosswalkRecord], result: ValidationResult) -> None:
    """Check 2 — Duplicate source-target pair."""
    counts = Counter((r.source_identifier, r.target_identifier) for r in records)
    for record in records:
        pair = (record.source_identifier, record.target_identifier)
        if counts[pair] > 1:
            result.add(
                "FAIL",
                f"source-target 쌍 중복: {record.source_identifier!r} -> {record.target_identifier!r}"
                f"(crosswalk_id={record.crosswalk_id!r})",
            )
        else:
            result.add(
                "PASS",
                f"source-target 쌍 유일성 확인: {record.source_identifier!r} -> {record.target_identifier!r}",
            )


def _check_missing_evidence(records: list[CrosswalkRecord], result: ValidationResult) -> None:
    """Check 3 — Missing evidence(Mapping Policy Rule 3)."""
    for record in records:
        if record.mapping_status in _EVIDENCE_REQUIRED_STATUSES:
            if not record.evidence or not record.evidence.strip():
                result.add(
                    "FAIL",
                    f"{record.crosswalk_id!r}: mapping_status={record.mapping_status.value!r}인데 evidence 누락",
                )
            else:
                result.add("PASS", f"{record.crosswalk_id!r}: evidence 존재 확인")
        else:
            result.add("PASS", f"{record.crosswalk_id!r}: mapping_status=unmapped, evidence 불필요")


def _check_invalid_mapping_status(records: list[CrosswalkRecord], result: ValidationResult) -> None:
    """Check 4 — Invalid mapping_status.

    schema.py의 enum이 이미 구조적으로 잘못된 값(예: 'auto-guessed')을
    생성 시점에 차단하므로, 여기서는 이미 CrosswalkRecord로 만들어진
    레코드가 Gate-eligible 값인지(§Rule 2 confidence 정합성 포함)를
    재확인하는 방어적 이중 검사로 동작한다.
    """
    for record in records:
        if record.mapping_status in _EXPLICITLY_FORBIDDEN_STATUS_STRINGS:
            # schema.py enum 강제로 인해 실질적으로 도달 불가능하지만,
            # 방어적으로 유지(작업 명령서 §4 Rule 1 명시 요구사항).
            result.add("FAIL", f"{record.crosswalk_id!r}: 금지된 mapping_status {record.mapping_status!r}")
            continue

        if record.mapping_status == MappingStatus.UNMAPPED:
            if record.confidence is not None:
                result.add(
                    "FAIL",
                    f"{record.crosswalk_id!r}: mapping_status=unmapped인데 confidence가 설정됨({record.confidence!r})",
                )
            else:
                result.add("PASS", f"{record.crosswalk_id!r}: unmapped 상태 정합성 확인")
        else:
            if record.confidence is None:
                result.add(
                    "FAIL",
                    f"{record.crosswalk_id!r}: mapping_status={record.mapping_status.value!r}인데 confidence 누락",
                )
            else:
                result.add(
                    "PASS",
                    f"{record.crosswalk_id!r}: mapping_status/confidence 정합성 확인"
                    f"(score={confidence_score(record.confidence)})",
                )


def _check_broken_identifier_reference(
    records: list[CrosswalkRecord],
    result: ValidationResult,
    valid_source_identifiers: set[str] | None,
) -> None:
    """Check 5 — Broken identifier reference(Registry/Manifest source_id 대조)."""
    if valid_source_identifiers is None:
        result.add("WARNING", "valid_source_identifiers 미제공 — Broken Reference 검사 생략")
        return

    for record in records:
        if record.source_identifier in valid_source_identifiers:
            result.add("PASS", f"{record.crosswalk_id!r}: source_identifier={record.source_identifier!r} Registry 참조 확인")
        else:
            result.add(
                "FAIL",
                f"{record.crosswalk_id!r}: source_identifier={record.source_identifier!r} — "
                f"Registry/Manifest source_id에 존재하지 않음(Broken Reference)",
            )
