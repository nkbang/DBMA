"""MTP 지정 volume들을 재청킹 + TSU 재색인.

기존 프로덕션 파이프라인을 그대로 재사용한다:
  1) core.processing.process_one_file (force_rechunk=True)
  2) core.index_orchestrator.reindex_document (TSU dataset + 후보 인덱스 + 성경 인덱스)

사용법:
    python3 scripts/spurgeon_reprocess_volumes.py --volumes 7,8,9
    python3 scripts/spurgeon_reprocess_volumes.py --range 7-63

반드시 ~/DBMA 저장소 루트에서, 프로젝트 venv(~/envs/dbma311/bin/python3)로 실행할 것.
data/제련완성본/Spurgeon_MTP_Vol{N}.txt 가 이미 존재해야 한다(스크레이퍼로 먼저 교체).
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.processing import build_converter, build_splitter, process_one_file
from core.config import DEFAULT_OUTPUT_DIR, DEFAULT_CHUNK_SIZE, DEFAULT_CHUNK_OVERLAP, registry_path_for
from core.identity_registry import load_identity_registry
from core.index_orchestrator import reindex_document


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--volumes", help="쉼표구분 volume 번호 목록, 예: 7,8,9")
    ap.add_argument("--range", help="시작-끝 volume 범위, 예: 7-63")
    args = ap.parse_args()

    if args.volumes:
        volumes = [int(v) for v in args.volumes.split(",")]
    elif args.range:
        lo, hi = args.range.split("-")
        volumes = list(range(int(lo), int(hi) + 1))
    else:
        raise SystemExit("--volumes 또는 --range 중 하나는 필수")

    output_dir = DEFAULT_OUTPUT_DIR
    converter = build_converter(use_ocr=False)
    splitter = build_splitter(DEFAULT_CHUNK_SIZE, DEFAULT_CHUNK_OVERLAP)

    results = []
    for vol in volumes:
        name = f"Spurgeon_MTP_Vol{vol}.txt"
        path = os.path.join(output_dir, name)
        if not os.path.exists(path):
            print(f"=== Vol{vol}: 스킵 (파일 없음: {path}) ===")
            results.append({"vol": vol, "success": False, "reason": "file_missing"})
            continue

        file_info = {"path": path, "name": name, "ext": "txt", "use_ocr": False}

        def report(stage, message, progress=None):
            print(f"  [{stage}] {message}")

        print(f"=== Vol{vol}: 재청킹 ===")
        result = process_one_file(
            file_info, converter, splitter, output_dir,
            DEFAULT_CHUNK_SIZE, DEFAULT_CHUNK_OVERLAP,
            report=report, force_rechunk=True,
        )
        print(f"Vol{vol}: success={result['success']} failed_stage={result.get('failed_stage')} reason={result.get('reason')}")
        if not result["success"]:
            results.append({"vol": vol, "success": False, "reason": result.get("reason")})
            continue

        # 방금 등록된 최신 document_id 조회 (superseded_by == None)
        registry_path = registry_path_for(output_dir)
        registry = load_identity_registry(registry_path)
        doc_id = None
        for did, d in registry.get("documents", {}).items():
            if d.get("source_file") == name and d.get("superseded_by") is None:
                doc_id = did
                break

        if doc_id is None:
            print(f"Vol{vol}: WARNING — registry에서 활성 document_id를 찾지 못함")
            results.append({"vol": vol, "success": False, "reason": "doc_id_not_found"})
            continue

        print(f"=== Vol{vol}: TSU 재색인 (document_id={doc_id[:16]}...) ===")
        reindex_result = reindex_document(doc_id, output_dir)
        print(f"Vol{vol}: replaced={reindex_result['replaced']} new={reindex_result['new']}")
        results.append({
            "vol": vol, "success": True, "document_id": doc_id,
            "chunks": reindex_result["new"],
        })
        print()

    print("=== 요약 ===")
    print(json.dumps(results, ensure_ascii=False, indent=2))
    failed = [r for r in results if not r["success"]]
    if failed:
        print(f"\n실패/스킵: {len(failed)}건")
        sys.exit(1)


if __name__ == "__main__":
    main()
