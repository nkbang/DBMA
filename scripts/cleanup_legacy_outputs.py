#!/usr/bin/env python
"""scripts/cleanup_legacy_outputs.py — output/registry, output/baseline, output_sav를 backups/로 이동 (C1-TASK-ORDER-007 항목5).

기본은 dry-run(목록만 출력) — 실제 이동은 --execute 플래그가 있어야 하고,
그 전에 반드시 backups/legacy_artifact_cleanup_{YYYYMMDD}/로 파일을 복사한다.

Usage:
    python scripts/cleanup_legacy_outputs.py              # dry-run
    python scripts/cleanup_legacy_outputs.py --execute     # 실제 이동 (백업 후)
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# 이동 대상 디렉터리 (Task Order §항목5에서 지정한 세 곳)
SOURCES = [
    Path("output/registry"),
    Path("output/baseline"),
    Path("output_sav"),
]

BACKUP_ROOT = Path("backups")


def find_existing_files() -> list[Path]:
    """이동 대상 디렉터리 안에 있는 실제 파일 목록을 반환."""
    files = []
    for src in SOURCES:
        if src.exists():
            for f in sorted(src.rglob("*")):
                if f.is_file():
                    files.append(f)
    return files


def dry_run() -> None:
    """이동될 파일 목록만 출력."""
    print("=" * 80)
    print("legacy output artifact 정리 — dry run")
    print("=" * 80)

    timestamp = datetime.now().strftime("%Y%m%d")
    backup_dir = BACKUP_ROOT / f"legacy_artifact_cleanup_{timestamp}"

    print(f"\n대상 디렉터리:")
    for src in SOURCES:
        if src.exists():
            count = sum(1 for _ in src.rglob("*") if _.is_file())
            size = sum(f.stat().st_size for f in src.rglob("*") if f.is_file())
            print(f"  {src}/  ({count}개 파일, {size:,} bytes)")
        else:
            print(f"  {src}/  (존재하지 않음 — 건너뜌)")

    files = find_existing_files()
    print(f"\n이동될 파일 총 {len(files)}개:")
    for f in files:
        rel = f.relative_to(".")
        print(f"  {rel}")

    print(f"\n--execute 없이 실행됨 — 아무것도 이동/삭제하지 않음.")
    print(f"백업 대상: {backup_dir}/")
    print("=" * 80)


def execute() -> None:
    """backups/로 실제 이동 수행."""
    timestamp = datetime.now().strftime("%Y%m%d")
    backup_dir = BACKUP_ROOT / f"legacy_artifact_cleanup_{timestamp}"
    backup_dir.mkdir(parents=True, exist_ok=True)

    moved = 0
    for src in SOURCES:
        if not src.exists():
            print(f"[skip] {src}/ — 존재하지 않음")
            continue

        for f in sorted(src.rglob("*")):
            if not f.is_file():
                continue
            dest = backup_dir / f.relative_to(".")
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(f), str(dest))
            moved += 1
            print(f"[moved] {f} -> {dest}")

    # 빈 디렉터리 정리 (하위부터)
    for src in SOURCES:
        if src.exists():
            try:
                src.rmdir()  # 비어있으면 성공
                print(f"[removed empty dir] {src}/")
            except OSError:
                pass  # 파일이 남아있음

    print(f"\n총 {moved}개 파일을 {backup_dir}/로 이동 완료.")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="dry-run 없이 실제 이동 수행",
    )
    args = parser.parse_args()

    if args.execute:
        execute()
    else:
        dry_run()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())