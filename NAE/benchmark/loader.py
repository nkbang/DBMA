"""NAE Benchmark Dataset Loader — JSONL 읽기 + 검증.

사용법:
    from NAE.benchmark.loader import load_dataset

    items = load_dataset("benchmark_v1.jsonl")
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from NAE.benchmark.schema import BenchmarkItem

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------

def load_dataset(
    path: str | Path,
    skip_malformed: bool = True,
) -> List[BenchmarkItem]:
    """JSONL 데이터셋을 로드하고 스키마 검증을 수행.

    Args:
        path: JSONL 파일 경로.
        skip_malformed: False이면 malformed record에서 예외를 던짐.

    Returns:
        검증 통과한 BenchmarkItem 목록.

    Raises:
        FileNotFoundError: 파일이 없을 때.
        ValueError: skip_malformed=False이고 record가 유효하지 않을 때.
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
    """한 줄을 BenchmarkItem으로 파싱.

    Returns:
        (item, error_message) — item이 있으면 error_message는 빈 문자열.
        item이 없으면 item은 None, error_message는 이유.
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

    return (item, "")


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