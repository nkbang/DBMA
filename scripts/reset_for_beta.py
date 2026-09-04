#!/usr/bin/env python
"""scripts/reset_for_beta.py — 베타 배포 전 전체 데이터 초기화.

테스터마다 자신의 파일로 새로 테스트하는 것을 전제로, RAW 원본을 포함한
모든 처리 산출물을 초기화한다(이전 exclude 기능의 backups/ 보존 원칙과
달리, 이 스크립트는 "이전 데이터 자체가 베타에 무의미"하다는 전제).

초기화 대상:
  1. data/RAW/                              — 원본 파일 (테스터가 새로 업로드)
  2. {output_dir}/                          — 처리된 chunk/.md/registry 전체
     (registry/documents.json은 삭제 대신 빈 스키마로 재생성)
  3. output/bench/tsu_dataset.jsonl, tsu_manifest.json — TSU 데이터셋만
     (같은 디렉토리의 gold_standard/baseline 벤치마크 파일은 평가 자산이라
     보존한다 — 삭제 대상 아님)
  4. chroma_db/                             — 벡터스토어 콘텐츠(디렉토리는 재생성)

기본은 dry-run(목록만 출력) — 실제 삭제는 --execute 플래그가 있어야 하고,
그 전에 반드시 backups/pre_beta_reset_{YYYYMMDD}/로 전체 백업한다
(scripts/cleanup_legacy_outputs.py와 동일한 안전 패턴).

Usage:
    python scripts/reset_for_beta.py              # dry-run
    python scripts/reset_for_beta.py --execute     # 실제 초기화 (백업 후)
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import DEFAULT_OUTPUT_DIR, DEFAULT_RAW_DIR, DEFAULT_TSU_DATASET_PATH, DEFAULT_TSU_MANIFEST_PATH, CHROMA_PERSIST_DIR, registry_path_for

BACKUP_ROOT = Path("backups")

# (경로, 설명) — 통째로 백업 후 비우는(디렉토리) 대상
RESET_DIRS = [
    (Path(DEFAULT_RAW_DIR), "RAW 원본"),
    (Path(DEFAULT_OUTPUT_DIR), "처리 산출물(chunk/.md/registry)"),
    (Path(CHROMA_PERSIST_DIR), "벡터스토어(Chroma)"),
]

# 개별 파일만 초기화 — 같은 디렉토리의 다른 파일(gold_standard/baseline 등
# 평가 자산)은 건드리지 않는다.
RESET_FILES = [
    (Path(DEFAULT_TSU_DATASET_PATH), "TSU 데이터셋"),
    (Path(DEFAULT_TSU_MANIFEST_PATH), "TSU 매니페스트"),
]

EMPTY_REGISTRY_SCHEMA = {
    "schema_version": "2.0",
    "processing_version": "1.1.x",
    "created_at": None,  # 실행 시점으로 채움
    "updated_at": None,
    "documents": {},
    "_meta": {"total_documents": 0},
}


def _backup_dir() -> Path:
    timestamp = datetime.now().strftime("%Y%m%d")
    return BACKUP_ROOT / f"pre_beta_reset_{timestamp}"


def dry_run() -> None:
    print("=" * 80)
    print("베타 배포 전 전체 데이터 초기화 — dry run")
    print("=" * 80)

    backup_dir = _backup_dir()

    print("\n[디렉토리 초기화 대상]")
    for path, desc in RESET_DIRS:
        if path.exists():
            count = sum(1 for _ in path.rglob("*") if _.is_file())
            size = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
            print(f"  {path}/  ({desc}, {count}개 파일, {size:,} bytes)")
        else:
            print(f"  {path}/  ({desc}, 존재하지 않음 — 건너뜀)")

    print("\n[개별 파일 초기화 대상]")
    for path, desc in RESET_FILES:
        if path.exists():
            print(f"  {path}  ({desc}, {path.stat().st_size:,} bytes)")
        else:
            print(f"  {path}  ({desc}, 존재하지 않음 — 건너뜀)")

    print(f"\n백업 대상: {backup_dir}/ (실제 삭제 전 전체 복사)")
    print("--execute 없이 실행됨 — 아무것도 삭제/초기화하지 않음.")
    print("=" * 80)


def execute() -> None:
    backup_dir = _backup_dir()
    backup_dir.mkdir(parents=True, exist_ok=True)

    # 1) 백업 (삭제 전 전체 복사 — 되돌릴 수 없는 작업의 안전망)
    for path, desc in RESET_DIRS:
        if path.exists() and any(path.rglob("*")):
            dest = backup_dir / path.name
            shutil.copytree(path, dest, dirs_exist_ok=True)
            print(f"[backup] {path}/ -> {dest}/")
    for path, desc in RESET_FILES:
        if path.exists():
            dest = backup_dir / "bench" / path.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dest)
            print(f"[backup] {path} -> {dest}")

    # 2) 디렉토리 비우기 (디렉토리 자체는 유지, 내용만 삭제)
    for path, desc in RESET_DIRS:
        if not path.exists():
            print(f"[skip] {path}/ — 존재하지 않음")
            continue
        for child in path.iterdir():
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
        print(f"[cleared] {path}/ ({desc})")

    # 3) registry는 완전 삭제가 아니라 빈 스키마로 재생성
    registry_path = Path(registry_path_for(DEFAULT_OUTPUT_DIR))
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    fresh = dict(EMPTY_REGISTRY_SCHEMA)
    now = datetime.now().isoformat(timespec="seconds")
    fresh["created_at"] = now
    fresh["updated_at"] = now
    registry_path.write_text(json.dumps(fresh, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[reset] {registry_path} — 빈 registry로 재생성")

    # 4) TSU 데이터셋/매니페스트 파일만 삭제 (같은 디렉토리의 gold_standard/
    #    baseline 벤치마크 파일은 평가 자산이라 보존)
    for path, desc in RESET_FILES:
        if path.exists():
            path.unlink()
            print(f"[removed] {path} ({desc})")

    print(f"\n초기화 완료 — 백업: {backup_dir}/")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--execute", action="store_true", help="dry-run 없이 실제 초기화 수행")
    args = parser.parse_args()

    if args.execute:
        execute()
    else:
        dry_run()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
