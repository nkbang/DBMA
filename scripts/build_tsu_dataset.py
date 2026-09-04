#!/usr/bin/env python3
"""scripts/build_tsu_dataset.py — TSU v1 batch builder (CLI wrapper).

SPRINT20-I-C-2-B: TSU 생성 라이브러리 로직은 core/tsu_builder.py로
승격되었다(Index Authority, docs/architecture/DBMA-Index-Authority-Design-v1.md).
이 파일은 이제 CLI wrapper만 담당한다 — argparse 인자 처리, dry-run,
파일 경로 조립, main().

라이브러리 함수(build_tsu_records/write_tsu_dataset/write_manifest 및
scripture resolver 헬퍼들)는 하위 호환을 위해 core.tsu_builder에서
re-export한다. 기존에 `from scripts.build_tsu_dataset import ...` 또는
`import scripts.build_tsu_dataset as mod`로 접근하던 코드/테스트가 그대로
동작한다(단, monkeypatch 대상은 실제 정의 위치인 core.tsu_builder로 옮겨야
효과가 있다 — SPRINT20-I-C-2-B에서 테스트 갱신 완료).

Usage:
    python -m scripts.build_tsu_dataset --output-dir output
    python -m scripts.build_tsu_dataset --output-dir output --dry-run

    # [docs/NAE_DATA_ARCHITECTURE.md §3] --dataset-path lets a caller point
    # at a non-default registry (e.g. a NAE-scoped output-dir) without
    # overwriting the shared production TSU dataset at DEFAULT_TSU_DATASET_PATH
    # — omitting the flag preserves the exact prior behavior.
    python -m scripts.build_tsu_dataset --output-dir data/nae/processed --dataset-path output/nae/bench/tsu_dataset.jsonl
"""

from __future__ import annotations

import argparse
import datetime
import json
from pathlib import Path

from core.identity_registry import load_identity_registry
from core.config import DEFAULT_OUTPUT_DIR, DEFAULT_TSU_DATASET_PATH, DEFAULT_TSU_MANIFEST_PATH, registry_path_for

# Backward-compatible re-export of the library layer (now core/tsu_builder.py).
from core.tsu_builder import (  # noqa: F401
    _CHUNK_HEADER_RE,
    _reference_parser,
    _resolve_scripture_ref,
    _resolve_chapter,
    _score_candidate,
    _resolve_evidence,
    _resolve_book_id,
    _read_chunk_texts,
    _read_md_fallback,
    build_tsu_records,
    write_tsu_dataset,
    _git_commit_hash,
    _sha256_of_file,
    write_manifest,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build TSU v1 dataset from the identity registry.")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help=f"Processing output directory (default: {DEFAULT_OUTPUT_DIR})")
    parser.add_argument(
        "--dataset-path",
        default=DEFAULT_TSU_DATASET_PATH,
        help=(
            f"TSU dataset output path (default: {DEFAULT_TSU_DATASET_PATH}). "
            "Override this when --output-dir points at a non-default registry "
            "(e.g. a NAE-scoped output-dir) so the write does not collide with "
            "the shared production TSU dataset — see docs/NAE_DATA_ARCHITECTURE.md §3."
        ),
    )
    parser.add_argument("--dry-run", action="store_true", help="Build in memory only; do not write files")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    registry_path = Path(registry_path_for(args.output_dir))
    dataset_path = Path(args.dataset_path)
    manifest_path = Path(DEFAULT_TSU_MANIFEST_PATH)

    registry = load_identity_registry(str(registry_path))
    records = build_tsu_records(registry, output_dir)

    if args.dry_run:
        print(f"[DRY-RUN] would write {len(records)} TSU records to {dataset_path}")
        for rec in records[:3]:
            print(json.dumps(rec, ensure_ascii=False))
        manifest = {
            "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
            "tsu_count": len(records),
            "source_document_count": len({r["document_id"] for r in records}),
        }
        print(f"[DRY-RUN] manifest: {json.dumps(manifest, ensure_ascii=False)}")
        return

    write_tsu_dataset(records, dataset_path)
    config_path = Path(__file__).resolve().parent.parent / "config.yaml"
    manifest = write_manifest(
        records, registry, manifest_path,
        registry_path=registry_path,
        dataset_path=dataset_path,
        config_path=config_path,
    )
    print(f"Wrote {len(records)} TSU records to {dataset_path}")
    print(f"Wrote manifest to {manifest_path}: {manifest}")


if __name__ == "__main__":
    main()
