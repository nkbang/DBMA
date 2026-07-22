#!/usr/bin/env python
"""scripts/dedupe_tsu_dataset.py — TSU dataset(output/bench/tsu_dataset.jsonl)
에서 cleanup_duplicate_outputs.py가 식별한 "진짜 중복" 원본의 레코드를
제거한다 (2026-07-21).

scripts/cleanup_duplicate_outputs.py의 find_size_duplicates() +
_pick_duplicate_keep_and_remove()를 그대로 재사용해 "삭제 대상
원본 파일명" 목록을 만든다 — 이 스크립트 안에서 한글 파일명을 직접
타이핑하지 않는다(터미널에서 수동으로 입력한 한글 문자열이 실제
디스크/JSON에 저장된 정규화 형태와 달라 매칭이 조용히 실패하는 문제가
이번 세션에서 반복 확인됐다 — Path 객체에서 유도된 문자열만 사용).

기본은 dry-run(매칭 레코드 수만 보고) — 실제 제거는 --execute 플래그가
있어야 하고, 그 전에 원본 jsonl을 backups/에 실제로 복사한다.

Usage:
    python scripts/dedupe_tsu_dataset.py              # dry-run
    python scripts/dedupe_tsu_dataset.py --execute      # 실제 제거 (백업 후)
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.cleanup_duplicate_outputs import (
    find_size_duplicates,
    _pick_duplicate_keep_and_remove,
)

TSU_DATASET_PATH = Path("output/bench/tsu_dataset.jsonl")
BACKUP_ROOT = Path("backups")


def get_remove_source_files() -> list[str]:
    """cleanup_duplicate_outputs.py와 완전히 동일한 로직으로 "삭제 대상
    원본 파일명" 목록을 유도한다 — 한글 리터럴을 여기서 새로 타이핑하지
    않음."""
    dup_groups = find_size_duplicates()
    remove_names: list[str] = []
    for g in dup_groups:
        _keep, remove = _pick_duplicate_keep_and_remove(g["pdfs"])
        remove_names.extend(p.name for p in remove)
    return remove_names


def plan() -> dict:
    remove_names = get_remove_source_files()
    remove_set = set(remove_names)

    matched_records: dict[str, int] = {}
    total = 0
    if TSU_DATASET_PATH.exists():
        with open(TSU_DATASET_PATH, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                total += 1
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                sf = rec.get("source_file", "")
                if sf in remove_set:
                    matched_records[sf] = matched_records.get(sf, 0) + 1

    return {"remove_names": remove_names, "matched_records": matched_records, "total": total}


def print_plan(p: dict) -> None:
    print("=" * 70)
    print("TSU dataset 중복 레코드 정리 계획")
    print("=" * 70)
    print(f"전체 레코드 수: {p['total']}")
    if not p["matched_records"]:
        print("삭제 대상 원본에 해당하는 TSU 레코드 없음 — 정리 불필요.")
        return
    total_remove = 0
    for sf, count in p["matched_records"].items():
        print(f"  - {sf}: {count}개 레코드 제거 예정")
        total_remove += count
    print(f"\n제거될 레코드 총합: {total_remove} / {p['total']}")
    print("(dry-run — 실제 제거하려면 --execute 플래그로 다시 실행하세요)")


def execute(p: dict) -> None:
    if not p["matched_records"]:
        print("제거할 레코드가 없어 실행하지 않습니다.")
        return

    remove_set = set(p["matched_records"].keys())

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = BACKUP_ROOT / f"dedupe_tsu_dataset_{timestamp}"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / TSU_DATASET_PATH.name
    shutil.copy2(TSU_DATASET_PATH, backup_path)
    print(f"백업 완료: {backup_path}")

    kept = 0
    removed = 0
    tmp_path = TSU_DATASET_PATH.with_suffix(".jsonl.tmp")
    with open(TSU_DATASET_PATH, encoding="utf-8") as fin, open(tmp_path, "w", encoding="utf-8") as fout:
        for line in fin:
            stripped = line.strip()
            if not stripped:
                continue
            rec = json.loads(stripped)
            if rec.get("source_file", "") in remove_set:
                removed += 1
                continue
            fout.write(stripped + "\n")
            kept += 1

    tmp_path.replace(TSU_DATASET_PATH)
    print(f"제거된 레코드: {removed}, 유지된 레코드: {kept}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true", help="실제 제거 실행 (기본은 dry-run)")
    args = parser.parse_args()

    p = plan()
    print_plan(p)

    if args.execute:
        print()
        execute(p)


if __name__ == "__main__":
    main()
