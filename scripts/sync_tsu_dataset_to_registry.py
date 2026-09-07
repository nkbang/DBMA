#!/usr/bin/env python
"""scripts/sync_tsu_dataset_to_registry.py — TSU 데이터셋/색인을 레지스트리
상태에 맞춘다: ingest_status == "EXCLUDED"인 문서의 TSU 레코드를 데이터셋에서
제거하고, 매니페스트와 후보/성경 색인을 재작성한다.

배경 (2026-09-07):
  core/index_orchestrator.py::reconcile_pending()이 pipeline_state == "PROCESSED"
  만 보고 ingest_status == "EXCLUDED"를 무시해, 제외 처리된 문서의 레코드가
  5초 주기 리컨사일러로 계속 데이터셋에 재삽입돼 왔다(같은 커밋에서
  reconcile_pending 필터 수정). 그 결과 누적된 "제외됐는데 데이터셋에는
  남아 있는" 레코드를 여기서 일괄 정리한다. 파이프라인 출력 폴더 오처리로
  등록된 유령 문서 98건(cleanup_phantom_registry_entries.py로 EXCLUDED 표시)
  포함.

동시성:
  cleanup_phantom_registry_entries.py와 동일하게 registry_lock() 안에서
  데이터셋/매니페스트/색인 재작성을 전부 수행 — reconcile_pending()도 같은
  lock을 쓰므로 앱이 떠 있어도 뒤에서 직렬화된다. 다만 색인 전체 재빌드가
  수 분 걸리므로 가급적 앱을 내리고 실행할 것.

Usage:
    python scripts/sync_tsu_dataset_to_registry.py            # dry-run
    python scripts/sync_tsu_dataset_to_registry.py --execute
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import (  # noqa: E402
    DEFAULT_BIBLE_INDEX_PATH,
    DEFAULT_CANDIDATE_INDEX_DIR,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_TSU_DATASET_PATH,
    DEFAULT_TSU_MANIFEST_PATH,
    registry_path_for,
)
from core.identity_registry import (  # noqa: E402
    load_identity_registry,
    registry_lock,
)
from core.tsu_builder import write_manifest  # noqa: E402

BACKUP_ROOT = Path("backups")


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--execute", action="store_true")
    args = ap.parse_args()

    registry_path = Path(registry_path_for(DEFAULT_OUTPUT_DIR))
    dataset_path = Path(DEFAULT_TSU_DATASET_PATH)
    manifest_path = Path(DEFAULT_TSU_MANIFEST_PATH)
    config_path = Path(__file__).resolve().parent.parent / "config.yaml"

    registry = load_identity_registry(str(registry_path))
    excluded = {
        doc_id for doc_id, d in registry.get("documents", {}).items()
        if d.get("ingest_status") == "EXCLUDED"
    }
    print(f"registry EXCLUDED 문서: {len(excluded)}")

    # 데이터셋에 남아 있는 EXCLUDED 레코드 수 계산(dry-run 정보)
    stale = 0
    total = 0
    with open(dataset_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            total += 1
            try:
                r = json.loads(s)
            except json.JSONDecodeError:
                continue
            if r.get("document_id") in excluded:
                stale += 1
    print(f"데이터셋 레코드: {total}, 그 중 EXCLUDED 문서 소속(제거 대상): {stale}")

    if not args.execute:
        print("\n[dry-run] --execute 를 붙이면 데이터셋 정리 + 매니페스트/색인 재빌드.")
        return 0

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = BACKUP_ROOT / f"tsu_sync_{ts}"
    backup_dir.mkdir(parents=True, exist_ok=True)
    for src in (dataset_path, manifest_path):
        if src.exists():
            shutil.copy2(src, backup_dir / src.name)
    print(f"[backup] {backup_dir}/")

    with registry_lock(str(registry_path)):
        registry = load_identity_registry(str(registry_path))
        excluded = {
            doc_id for doc_id, d in registry.get("documents", {}).items()
            if d.get("ingest_status") == "EXCLUDED"
        }

        kept: list[dict] = []
        purged = bad = 0
        tmp = dataset_path.with_name(dataset_path.name + ".sync.tmp")
        with open(dataset_path, "r", encoding="utf-8", errors="replace") as fin, \
             open(tmp, "w", encoding="utf-8") as fout:
            for line in fin:
                s = line.strip()
                if not s:
                    continue
                try:
                    rec = json.loads(s)
                except json.JSONDecodeError:
                    bad += 1
                    continue
                if rec.get("document_id") in excluded:
                    purged += 1
                    continue
                kept.append(rec)
                fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
        tmp.replace(dataset_path)
        print(f"[tsu] EXCLUDED 레코드 {purged}건 + 파싱 불가 {bad}건 제거, {len(kept)}건 유지")

        registry_view = {
            **registry,
            "documents": {
                i: d for i, d in registry.get("documents", {}).items()
                if d.get("ingest_status") != "EXCLUDED"
            },
        }
        m = write_manifest(
            kept, registry_view, manifest_path,
            registry_path=registry_path, dataset_path=dataset_path, config_path=config_path,
        )
        print(f"[manifest] tsu_count={m['tsu_count']}, source_document_count={m['source_document_count']}")

        # 후보 색인: 손상/스테일 상태일 수 있으므로 디렉터리를 비우고 전체 재빌드
        from core.candidate_generator import build_index as build_candidate_index
        from core.bible_index import build_index as build_bible_index

        cand_dir = Path(DEFAULT_CANDIDATE_INDEX_DIR)
        if cand_dir.exists():
            shutil.rmtree(cand_dir)
        n = build_candidate_index(dataset_path, cand_dir)
        print(f"[candidate-index] 전체 재빌드: {n}건")

        bible_path = Path(DEFAULT_BIBLE_INDEX_PATH)
        n = build_bible_index(dataset_path, bible_path)  # build_index가 기존 파일 unlink 후 재생성
        print(f"[bible-index] 전체 재빌드: {n}건")

    print("\n완료.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
