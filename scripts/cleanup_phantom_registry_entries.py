#!/usr/bin/env python
"""scripts/cleanup_phantom_registry_entries.py — 파이프라인 출력 폴더
오처리로 레지스트리에 등록된 "유령 문서"를 일괄 정리한다.

배경 (2026-09-07):
  ui/pages/processing.py::_render_ingestion_form()의 폴더 후보가
  파이프라인 출력 폴더(data/제련완성본, DEFAULT_OUTPUT_DIR)까지 포함해,
  2026-09-07 14:20 처리 실행이 그 폴더를 대상으로 돌면서 변환 .md·청크
  덤프 산출물(`<원본>_pdf.md`, `<원본>_pdf_chunks.txt`, `<원본>_md.md`,
  `<원본>_md_chunks.txt` …)이 신규 "문서"로 registry에 등록됐다.
  → 대시보드 "정리된 자료"가 보유 문서 수를 초과(107 < 200).

정리 대상 판별 (두 조건을 모두 만족해야만 대상):
  1. source_file이 RAW 라이브러리에 존재하지 않는다(NFC 정규화 후 비교).
  2. source_file이 파이프라인 산출물 이름 규칙에 맞는다
     (_chunks.txt / _chunks_meta.json / _<지원확장자>.md).
  이미 EXCLUDED 상태인 항목은 건너뛴다.
  조건 1만 만족(사용자가 Finder에서 원본을 직접 지운 진짜 케이스)하고
  조건 2는 아닌 항목은 절대 건드리지 않는다.

동시성 (중요):
  core/background_index_builder.py가 5초마다 reconcile_pending()을 호출하며,
  그 함수는 registry_lock() 하나로 registry + tsu_dataset.jsonl 쓰기를 모두
  감싼다. 이 스크립트도 registry 표시 + 데이터셋/매니페스트/색인 재작성
  전체를 같은 registry_lock() 안에서 수행하므로, 앱이 떠 있어도
  reconcile_pending()은 이 lock 뒤에서 직렬화되어 경쟁이 발생하지 않는다.
  (2026-09-07 1차 시도에서 lock 밖에서 데이터셋을 재작성해 리컨사일러와
  쓰기 경쟁 → 데이터셋 오염. 백업에서 복원 후 이 구조로 재작성함.)

수행 작업 (--execute 시, registry_lock 보유):
  a. backups/phantom_registry_cleanup_{ts}/ 에 원본 3종 백업.
  b. registry: 대상 98건을 ingest_status="EXCLUDED",
     pipeline_state="INDEXED"(리컨사일러 재스캔 방지)로 표시하고 저장.
  c. TSU 데이터셋: 파싱 불가한 줄 + 대상 document_id 레코드 제거, 1회 재작성.
  d. tsu_manifest.json 재작성(EXCLUDED 제외한 registry 기준 count).
  e. 후보 색인(tantivy) / 성경 색인(sqlite)을 정리된 데이터셋으로 전체 재빌드.
  (lock 해제 후) f. data/제련완성본/의 {stem}_chunks.txt /
     {stem}_chunks_meta.json / {stem}.md 파생 파일을
     backups/excluded_documents_{YYYYMMDD}/로 이동.

Usage:
    python scripts/cleanup_phantom_registry_entries.py            # dry-run
    python scripts/cleanup_phantom_registry_entries.py --execute   # 실제 정리
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import (  # noqa: E402
    DEFAULT_BIBLE_INDEX_PATH,
    DEFAULT_CANDIDATE_INDEX_DIR,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_RAW_DIR,
    DEFAULT_TSU_DATASET_PATH,
    DEFAULT_TSU_MANIFEST_PATH,
    SUPPORTED_EXTENSIONS,
    registry_path_for,
)
from core.identity_registry import (  # noqa: E402
    exclude_document,
    load_identity_registry,
    registry_lock,
    save_identity_registry,
)
from core.tsu_builder import write_manifest, write_tsu_dataset  # noqa: E402
from core.utils import make_safe_stem  # noqa: E402

BACKUP_ROOT = Path("backups")


def _is_pipeline_artifact_name(source_file: str) -> bool:
    """ui/pages/dashboard.py::_is_pipeline_artifact_name()와 동일 규칙.
    (스크립트 독립 실행을 위해 여기 복제 — 규칙이 바뀌면 양쪽 함께 수정.)"""
    if not source_file:
        return False
    name = source_file.strip().lower()
    if name.endswith("_chunks.txt") or name.endswith("_chunks_meta.json"):
        return True
    return any(name.endswith(f"_{ext.lstrip('.')}.md") for ext in SUPPORTED_EXTENSIONS)


def _raw_source_names() -> set[str]:
    raw_dir = Path(DEFAULT_RAW_DIR)
    if not raw_dir.exists():
        return set()
    return {
        unicodedata.normalize("NFC", f.name)
        for f in raw_dir.rglob("*")
        if f.is_file() and not f.name.startswith(".") and f.suffix.lower() in SUPPORTED_EXTENSIONS
    }


def find_phantom_documents(registry: dict) -> tuple[dict[str, str], list[tuple[str, str]]]:
    """Returns (targets, genuine_orphans).

    targets          — {document_id: source_file} 정리 대상(유령).
    genuine_orphans  — [(document_id, source_file)] RAW에 없지만 산출물
                       이름이 아닌 항목 — 건드리지 않고 보고만 한다.
    """
    raw_names = _raw_source_names()
    targets: dict[str, str] = {}
    genuine_orphans: list[tuple[str, str]] = []
    for doc_id, doc in registry.get("documents", {}).items():
        if doc.get("ingest_status") == "EXCLUDED":
            continue
        source_file = doc.get("source_file", "") or ""
        if unicodedata.normalize("NFC", source_file) in raw_names:
            continue
        if _is_pipeline_artifact_name(source_file):
            targets[doc_id] = source_file
        else:
            genuine_orphans.append((doc_id, source_file))
    return targets, genuine_orphans


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--execute", action="store_true", help="실제 정리 수행(기본은 dry-run)")
    args = ap.parse_args()

    output_dir = DEFAULT_OUTPUT_DIR
    registry_path = Path(registry_path_for(output_dir))
    dataset_path = Path(DEFAULT_TSU_DATASET_PATH)
    manifest_path = Path(DEFAULT_TSU_MANIFEST_PATH)

    registry = load_identity_registry(str(registry_path))
    targets, genuine_orphans = find_phantom_documents(registry)

    print(f"레지스트리 전체 문서: {len(registry.get('documents', {}))}")
    print(f"정리 대상(유령) 문서: {len(targets)}")
    print(f"보존되는 진짜 고아(원본만 삭제됨, 산출물 아님): {len(genuine_orphans)}")
    for doc_id, sf in genuine_orphans:
        print(f"  [보존] {doc_id[:12]}  {sf}")

    if not targets:
        print("정리할 유령 항목이 없습니다.")
        return 0

    print("\n--- 정리 대상 목록 ---")
    for doc_id, sf in sorted(targets.items(), key=lambda kv: kv[1]):
        print(f"  {doc_id[:12]}  {sf}")

    if not args.execute:
        print("\n[dry-run] --execute 를 붙이면 실제로 정리합니다. 변경 없음.")
        return 0

    # ── a. 백업 ──────────────────────────────────────────────────────
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = BACKUP_ROOT / f"phantom_registry_cleanup_{ts}"
    backup_dir.mkdir(parents=True, exist_ok=True)
    for src in (dataset_path, registry_path, manifest_path):
        if src.exists():
            shutil.copy2(src, backup_dir / src.name)
    print(f"\n[backup] {backup_dir}/ 복사 완료")

    target_ids = set(targets)
    config_path = Path(__file__).resolve().parent.parent / "config.yaml"

    # ── registry_lock 보유: b + c + d + e ──────────────────────────
    #   reconcile_pending()도 이 lock으로 registry+dataset 쓰기를 감싸므로
    #   이 블록 동안 리컨사일러는 완전히 대기한다.
    with registry_lock(str(registry_path)):
        # b. registry 표시
        registry = load_identity_registry(str(registry_path))
        marked = 0
        for doc_id in target_ids:
            rec = registry["documents"].get(doc_id)
            if rec is None:
                continue
            exclude_document(
                registry, doc_id,
                reason="파이프라인 출력 폴더 오처리로 잘못 등록된 산출물 - 일괄 정리 2026-09-07",
            )
            rec["pipeline_state"] = "INDEXED"  # 리컨사일러 pending 재스캔 방지(이중 안전장치)
            marked += 1
        save_identity_registry(registry, str(registry_path))
        print(f"[registry] {marked}건 EXCLUDED + pipeline_state=INDEXED 표시 후 저장")

        # c. TSU 데이터셋 재작성 (파싱 불가 줄 + 대상 레코드 제거)
        kept: list[dict] = []
        purged = bad = 0
        tmp = dataset_path.with_name(dataset_path.name + ".cleaned.tmp")
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
                if rec.get("document_id") in target_ids:
                    purged += 1
                    continue
                kept.append(rec)
                fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
        tmp.replace(dataset_path)
        print(f"[tsu] 유령 레코드 {purged}건 + 파싱 불가 줄 {bad}건 제거, {len(kept)}건 유지")

        # d. manifest 재작성 (EXCLUDED 제외한 registry 뷰 기준)
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

        # e. 후보 / 성경 색인 전체 재빌드 (정리된 데이터셋 기준, 증분 삭제 아님)
        from core.candidate_generator import build_index as build_candidate_index
        from core.bible_index import build_index as build_bible_index

        cand_dir = Path(DEFAULT_CANDIDATE_INDEX_DIR)
        if (cand_dir / "meta.json").exists() or cand_dir.exists():
            n = build_candidate_index(dataset_path, cand_dir)
            print(f"[candidate-index] 전체 재빌드 완료: {n}건")
        bible_path = Path(DEFAULT_BIBLE_INDEX_PATH)
        if bible_path.exists():
            n = build_bible_index(dataset_path, bible_path)
            print(f"[bible-index] 전체 재빌드 완료: {n}건")

    # ── f. 파생 산출물 파일 이동 (lock 불필요) ─────────────────────
    day = datetime.now().strftime("%Y%m%d")
    excl_dir = BACKUP_ROOT / f"excluded_documents_{day}"
    out_dir = Path(output_dir)
    moved = 0
    for doc_id, sf in targets.items():
        stem = make_safe_stem(sf)
        for cand in (out_dir / f"{stem}_chunks.txt",
                     out_dir / f"{stem}_chunks_meta.json",
                     out_dir / f"{stem}.md"):
            if cand.exists():
                excl_dir.mkdir(parents=True, exist_ok=True)
                shutil.move(str(cand), str(excl_dir / cand.name))
                moved += 1
    print(f"[files] 파생 산출물 {moved}개 → {excl_dir}/")

    print("\n완료. 되돌리려면 backups/phantom_registry_cleanup_*/ 의 3개 파일을 "
          "원위치로 복사하고 identity_registry.unexclude_document()를 실행하세요.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
