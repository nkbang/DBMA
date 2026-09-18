#!/usr/bin/env python
# DEPRECATED (ADR-033): 신규 리셋은 scripts/reset_workspace.py 를 사용한다
# (티어드 T1/T2, 2-층위 Protected Paths, 매니페스트). 이 스크립트는 RAW 포함
# 전체 wipe(= ADR-033 T3 범위, 현재 미구현)를 담당하며, 처리 방향
# (reset_workspace.py --tier T3 wrapper 로 축소 vs 완전 폐기)은 HQ 승인 대기.
# 그때까지 동작은 그대로 보존한다.
# [2026-09-18, HQ 결정] 배포판을 베타/정식으로 이원화하지 않기로 함 — 이
# 스크립트 이름·docstring의 "베타"는 과거 명칭 잔재이며, 실제로는 "배포
# 준비용 초기화 + 기본 코퍼스 재적재" 유틸리티다. 기능/이름 자체의 구조적
# 변경(리네임 등)은 core/retrieval.py, tests/test_reset_for_beta_reseed.py
# 등 참조가 많아 별도 작업으로 미룬다.
"""scripts/reset_for_beta.py — 배포 전 전체 데이터 초기화 + 기본 코퍼스 재적재.

테스터마다 자신의 파일로 새로 테스트하는 것을 전제로, RAW 원본을 포함한
모든 처리 산출물을 초기화한다(이전 exclude 기능의 backups/ 보존 원칙과
달리, 이 스크립트는 "개발자가 테스트하며 넣은 데이터 자체가 배포판에
무의미하다"는 전제).

[2026-09-15, S5 선결 — reset_for_beta.py ↔ NAE_FREE_DISTRIBUTION_PLAN_v1.md
"① 기본 동봉" 충돌 해소] 원래 이 스크립트는 초기화 후 아무것도 다시 채우지
않았다 — 그런데 배포판은 첫 실행부터 쓸 수 있는 퍼블릭 도메인 기본 코퍼스
(스펄전 등 67종, `scripts/baseline_corpus_manifest.json`)를 동봉해야 한다는
계획과 정면으로 충돌했다: 이 스크립트를 그대로 실행하면 그 코퍼스가
지워진 채로 패키징된다. 그래서 **초기화 직후 매니페스트 기준으로 기본
코퍼스를 다시 적재**하도록 바꿨다 — "개발자 테스트 잔재는 지우되, 검증된
퍼블릭 도메인 기본 서재는 항상 되돌아온다"가 새 계약이다.
`--no-reseed`로 예전처럼 완전히 빈 상태로 남길 수 있다(예: B-1 "자료
0건" 안전장치를 수동으로 재현해 볼 때).

초기화 대상:
  1. data/RAW/                              — 원본 파일(모두 삭제 후 재적재)
  2. {output_dir}/                          — 처리된 chunk/.md/registry 전체
     (registry/documents.json은 삭제 대신 빈 스키마로 재생성)
  3. output/bench/tsu_dataset.jsonl, tsu_manifest.json — TSU 데이터셋만
     (같은 디렉토리의 gold_standard/baseline 벤치마크 파일은 평가 자산이라
     보존한다 — 삭제 대상 아님)
  4. chroma_db/                             — 벡터스토어 콘텐츠(디렉토리는 재생성)

재적재 대상(기본 동작, --no-reseed로 끌 수 있음):
  `scripts/baseline_corpus_manifest.json`에 실린 항목을
  `<source_root>/<source_dir>/<source_file_in_dir>`에서 찾아 `data/RAW/`에
  복사하고, `ui/pages/processing.py`와 동일한 파이프라인(build_converter→
  build_splitter→process_batch→reconcile_pending)으로 처리한다. 원본
  아카이브(`~/NAE_CORPUS_RAW/...`, 기본 경로)가 이 기기에 없으면 항목별로
  건너뛰고 경고만 남긴다 — 재적재 실패가 초기화 자체를 막지 않는다.

기본은 dry-run(목록만 출력) — 실제 삭제는 --execute 플래그가 있어야 하고,
그 전에 반드시 backups/pre_beta_reset_{YYYYMMDD}/로 전체 백업한다
(scripts/cleanup_legacy_outputs.py와 동일한 안전 패턴).

Usage:
    python scripts/reset_for_beta.py                  # dry-run
    python scripts/reset_for_beta.py --execute         # 초기화 + 기본 코퍼스 재적재
    python scripts/reset_for_beta.py --execute --no-reseed   # 초기화만(완전히 빈 상태)
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
BASELINE_MANIFEST_PATH = Path(__file__).parent / "baseline_corpus_manifest.json"

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
    print("배포 전 전체 데이터 초기화 — dry run")
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

    print("\n[초기화 후 재적재]")
    if BASELINE_MANIFEST_PATH.exists():
        manifest = json.loads(BASELINE_MANIFEST_PATH.read_text(encoding="utf-8"))
        source_root = Path(manifest["source_root"]).expanduser()
        status = "존재함" if source_root.exists() else "존재하지 않음 — 재적재는 건너뛰어짐"
        print(f"  {manifest['count']}건, 원본 아카이브 {source_root}({status})")
        print("  --no-reseed로 끄지 않으면 초기화 직후 자동 재적재됨")
    else:
        print(f"  매니페스트 없음({BASELINE_MANIFEST_PATH}) — 재적재 안 됨")

    print("\n--execute 없이 실행됨 — 아무것도 삭제/초기화하지 않음.")
    print("=" * 80)


def reseed_baseline() -> None:
    """초기화 직후 `baseline_corpus_manifest.json` 기준으로 퍼블릭 도메인
    기본 코퍼스를 다시 적재한다. `ui/pages/processing.py`와 동일한 파이프
    라인을 헤드리스로 재현한다(ADR-001 무위반 — 새 검색/처리 경로 아님).

    원본 아카이브가 이 기기에 없는 항목은 건너뛰고 경고만 남긴다 — 재적재
    실패가 초기화 자체를 실패로 만들지 않는다(초기화는 이미 끝난 뒤라
    되돌릴 필요도 없다).
    """
    if not BASELINE_MANIFEST_PATH.exists():
        print(f"[reseed] 매니페스트 없음({BASELINE_MANIFEST_PATH}) — 재적재 건너뜀")
        return

    manifest = json.loads(BASELINE_MANIFEST_PATH.read_text(encoding="utf-8"))
    source_root = Path(manifest["source_root"]).expanduser()
    source_file_name = manifest["source_file_in_dir"]
    entries = manifest["entries"]

    if not source_root.exists():
        print(
            f"[reseed] 원본 아카이브 없음({source_root}) — 기본 코퍼스 재적재를 "
            f"건너뜀. 이 기기가 원본을 보유한 개발 기기가 아니면 정상이다. "
            f"data/RAW는 빈 상태로 남는다."
        )
        return

    raw_dir = Path(DEFAULT_RAW_DIR)
    raw_dir.mkdir(parents=True, exist_ok=True)

    file_list = []
    missing = []
    for entry in entries:
        src = source_root / entry["source_dir"] / source_file_name
        if not src.exists():
            missing.append(entry["filename"])
            continue
        dest = raw_dir / entry["filename"]
        dest.write_bytes(src.read_bytes())
        file_list.append({
            "path": str(dest), "name": entry["filename"], "ext": "txt", "use_ocr": False,
        })

    if missing:
        print(f"[reseed] 원본 누락 {len(missing)}건 — 건너뜀: {', '.join(missing[:5])}"
              f"{' ...' if len(missing) > 5 else ''}")
    if not file_list:
        print("[reseed] 재적재할 파일이 하나도 없음 — 중단")
        return

    print(f"[reseed] {len(file_list)}개 기본 코퍼스 파일 처리 중...")
    from core.processing import build_converter, build_splitter, process_batch
    from core.index_orchestrator import reconcile_pending

    converter = build_converter(use_ocr=False)
    splitter = build_splitter(chunk_size=1200, chunk_overlap=120)
    results = process_batch(
        file_list=file_list, converter=converter, splitter=splitter,
        output_dir=DEFAULT_OUTPUT_DIR, chunk_size=1200, chunk_overlap=120,
        force_reingest=False, force_rechunk=False,
    )
    success = sum(1 for r in results if r.get("success"))
    print(f"[reseed] 처리 완료 — 성공 {success}/{len(file_list)}")

    recon = reconcile_pending(DEFAULT_OUTPUT_DIR)
    print(f"[reseed] reconcile_pending: {recon}")


def execute(reseed: bool = True) -> None:
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

    if reseed:
        print("\n" + "=" * 80)
        print("기본 코퍼스 재적재")
        print("=" * 80)
        reseed_baseline()
    else:
        print("\n--no-reseed 지정됨 — 기본 코퍼스를 다시 채우지 않고 빈 상태로 남김.")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--execute", action="store_true", help="dry-run 없이 실제 초기화 수행")
    parser.add_argument(
        "--no-reseed", action="store_true",
        help="초기화 후 기본 코퍼스(baseline_corpus_manifest.json)를 다시 채우지 않는다"
             " — 완전히 빈 상태가 필요할 때만(예: B-1 자료 0건 안전장치 수동 재현)",
    )
    args = parser.parse_args()

    if args.execute:
        execute(reseed=not args.no_reseed)
    else:
        dry_run()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
