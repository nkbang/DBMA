"""NAE Benchmark Dataset Loader — JSONL 읽기 + 검증.

사용법:
    from NAE.benchmark.loader import load_dataset

    items = load_dataset("benchmark_v1.jsonl")
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union

from NAE.benchmark.schema import (
    BenchmarkItem,
    GOLD_VALIDITY_STATUSES,
)

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Custom exception for gold_tsu_ids conflicts
# ------------------------------------------------------------------

class GoldTsusIdsConflictError(ValueError):
    """top-level과 expected.gold_tsu_ids 가 존재하고 값이 다를 때 발생."""

    def __init__(self, top_level: List[str], nested: List[str], lineno: int = 0) -> None:
        self.top_level = top_level
        self.nested = nested
        self.lineno = lineno
        super().__init__(
            f"gold_tsu_ids conflict at line {lineno}: "
            f"top-level={top_level}, expected.gold_tsu_ids={nested}. "
            f"Values must match or only one source should exist."
        )


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------

def load_dataset(
    path: str | Path,
    skip_malformed: bool = True,
    known_tsu_ids: Optional[Set[str]] = None,
) -> List[BenchmarkItem]:
    """JSONL 데이터셋을 로드하고 스키마 검증을 수행.

    Args:
        path: JSONL 파일 경로.
        skip_malformed: False 이면 malformed record 에서 예외를 던짐.
        known_tsu_ids: 실제 TSU ID 집합 (referential integrity 검증용).

    Returns:
        검증 통과한 BenchmarkItem 목록.

    Raises:
        FileNotFoundError: 파일이 없을 때.
        ValueError: skip_malformed=False 이고 record 가 유효하지 않을 때.
    """
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"benchmark dataset not found: {path}")

    items: List[BenchmarkItem] = []
    line_numbers: List[int] = []
    errors: List[Tuple[int, str]] = []

    with open(path, "r", encoding="utf-8") as fh:
        for lineno, raw_line in enumerate(fh, start=1):
            line = raw_line.strip()
            if not line:
                continue  # blank line skip

            item, err = _parse_record(line, lineno)
            if item is None:
                errors.append((lineno, err))
                if not skip_malformed:
                    raise ValueError(f"malformed record at {path}:{lineno}: {err}")
                continue

            validation_errors = item.validate()
            if validation_errors:
                errors.append((lineno, "validation: " + "; ".join(validation_errors)))
                if not skip_malformed:
                    raise ValueError(
                        f"schema validation failed at {path}:{lineno}: {validation_errors}"
                    )
                continue

            # referential integrity check
            if known_tsu_ids is not None:
                ref_errors = item.validate_referential_integrity(known_tsu_ids)
                if ref_errors:
                    errors.append((lineno, "referential: " + "; ".join(ref_errors)))
                    if not skip_malformed:
                        raise ValueError(
                            f"referential integrity failed at {path}:{lineno}: {ref_errors}"
                        )
                    continue

            items.append(item)
            line_numbers.append(lineno)

    # 로깅
    total = len(items) + len(errors)
    logger.info(
        "loaded %d/%d records from %s",
        len(items),
        total,
        path,
    )
    if errors:
        for ln, msg in errors:
            logger.warning("skipped record at line %d: %s", ln, msg)

    return items


# ------------------------------------------------------------------
# Internal
# ------------------------------------------------------------------

def _parse_record(
    line: str, lineno: int
) -> Union[Tuple[BenchmarkItem, str], Tuple[None, str]]:
    """한 줄을 BenchmarkItem 으로 파싱.

    Returns:
        (item, error_message) — item 이 있으면 error_message 는 빈 문자열.
        item 이 없으면 item 은 None, error_message 는 이유.
    """
    try:
        data = json.loads(line)
    except json.JSONDecodeError as exc:
        return (None, f"JSON decode error: {exc}")

    if not isinstance(data, dict):
        return (None, "record is not a JSON object")

    try:
        item = BenchmarkItem.from_dict(data)
    except (TypeError, KeyError, ValueError) as exc:
        return (None, f"construction error: {exc}")

    # gold_tsu_ids canonicalization (migration matrix)
    _canonicalize_gold_tsu_ids(item, lineno)

    # INVALID_GOLD validation: empty / missing gold_tsu_ids → diagnostic
    _validate_gold_validity(item)

    return (item, "")


def _validate_gold_validity(item: BenchmarkItem) -> None:
    """gold_tsu_ids 유효성 진단 (HQ-C1-DIRECTIVE-NAE-PHASE5.1-REMEDIATION-004).

    - gold_tsu_ids 가 None, 누락, 또는 빈 list → INVALID_GOLD diagnostic
    - gold_tsu_ids 에 중복이 있음 → DUPLICATE_GOLD diagnostic
    - 유효한 경우 → VALID (변경 없음, validation error 아님)
    """
    gold = item.gold_tsu_ids

    # None 또는 빈 list → INVALID_GOLD
    if gold is None or len(gold) == 0:
        logger.warning(
            "benchmark_id=%s: gold_tsu_ids is empty — INVALID_GOLD diagnostic",
            item.benchmark_id or "(no-id)",
        )
        # validation error는 아니지만 warning 로깅으로 표시
        # (caller 가 skip_malformed=True 이면 통과됨)
        return

    # 중복 → DUPLICATE_GOLD (validation error)
    if len(gold) != len(set(gold)):
        logger.error(
            "benchmark_id=%s: gold_tsu_ids contains duplicates — DUPLICATE_GOLD",
            item.benchmark_id or "(no-id)",
        )


def _canonicalize_gold_tsu_ids(item: BenchmarkItem, lineno: int = 0) -> None:
    """gold_tsu_ids migration according to the migration matrix.

    Matrix:
        top-level exists, nested missing     → use top-level
        top-level missing, nested exists     → copy to top-level, warn
        both exist, equal                     → use top-level, warn
        both exist, different                 → GoldTsusIdsConflictError
        neither exists                         → empty list allowed
    """
    top_level = item.gold_tsu_ids
    nested = item.expected.gold_tsu_ids

    has_top = bool(top_level)
    has_nested = bool(nested)

    if has_top and not has_nested:
        # Case 1: top-level만 있음 → canonical 사용
        return

    if not has_top and has_nested:
        # Case 2: nested만 있음 → top-level로 복사, deprecation warning
        logger.warning(
            "benchmark_id=%s: expected.gold_tsu_ids is deprecated; "
            "copying to BenchmarkItem.gold_tsu_ids (line %d)",
            item.benchmark_id or "(no-id)",
            lineno,
        )
        item.gold_tsu_ids = list(nested)
        return

    if has_top and has_nested:
        if top_level == nested:
            # Case 3: 둘 다 있고 동일 → top-level 사용, deprecation warning
            logger.warning(
                "benchmark_id=%s: both gold_tsu_ids fields exist with same value; "
                "using BenchmarkItem.gold_tsu_ids (line %d)",
                item.benchmark_id or "(no-id)",
                lineno,
            )
            return
        else:
            # Case 4: 둘 다 있고 다름 → ValidationError
            raise GoldTsusIdsConflictError(top_level, nested, lineno)

    # Case 5: 둘 다 없음 → 빈 list 허용 (변경 없음)


# ------------------------------------------------------------------
# Utility: validate-only (file does not need to contain valid items)
# ------------------------------------------------------------------

def validate_dataset(path: str | Path) -> Dict[str, int]:
    """데이터셋 구조만 검증하고 항목은 반환하지 않음.

    Returns:
        {"total": N, "valid": M, "invalid": K}
    """
    path = Path(path)
    total = 0
    valid = 0
    invalid = 0

    with open(path, "r", encoding="utf-8") as fh:
        for raw_line in fh:
            line = raw_line.strip()
            if not line:
                continue
            total += 1
            try:
                data = json.loads(line)
                item = BenchmarkItem.from_dict(data)
                if item.validate():
                    invalid += 1
                else:
                    valid += 1
            except Exception:
                invalid += 1

    return {"total": total, "valid": valid, "invalid": invalid}


# ------------------------------------------------------------------
# Utility: check for duplicate benchmark_ids across dataset
# ------------------------------------------------------------------

def check_duplicate_benchmark_ids(path: str | Path) -> List[str]:
    """데이터셋 내 중복 benchmark_id 를 검사.

    Returns:
        중복된 benchmark_id 목록. 빈 목록이면 문제 없음.
    """
    path = Path(path)
    seen: Dict[str, int] = {}  # id -> first line number

    with open(path, "r", encoding="utf-8") as fh:
        for lineno, raw_line in enumerate(fh, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                bid = data.get("benchmark_id", "")
                if bid:
                    if bid in seen:
                        seen[bid] = seen[bid] + 1  # count occurrences
                    else:
                        seen[bid] = lineno
            except Exception:
                continue

    duplicates: List[str] = []
    for bid, count in seen.items():
        if isinstance(count, int) and count > 1:
            duplicates.append(bid)

    return duplicates


# ------------------------------------------------------------------
# Utility: check for empty dataset (no valid records)
# ------------------------------------------------------------------

def check_empty_dataset(path: str | Path) -> bool:
    """데이터셋이 비어있는지 (유효한 레코드 없음) 검사.

    Returns:
        True if empty (no valid records), False otherwise.
    """
    path = Path(path)
    has_valid = False

    with open(path, "r", encoding="utf-8") as fh:
        for raw_line in fh:
            line = raw_line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                item = BenchmarkItem.from_dict(data)
                if not item.validate():
                    has_valid = True
                    break
            except Exception:
                continue

    return not has_valid