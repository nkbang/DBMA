"""MTP Vol51/52/53 재청킹 — chspurgeon.com 교체본 반영.

기존 프로덕션 파이프라인(core.processing.process_one_file)을 그대로
재사용한다. force_rechunk=True로 콘텐츠 해시가 달라졌으니(내용 자체가
교체됨) 정상적으로 REPROCESS 경로를 탄다.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.processing import build_converter, build_splitter, process_one_file
from core.config import DEFAULT_OUTPUT_DIR, DEFAULT_CHUNK_SIZE, DEFAULT_CHUNK_OVERLAP

output_dir = DEFAULT_OUTPUT_DIR
converter = build_converter(use_ocr=False)
splitter = build_splitter(DEFAULT_CHUNK_SIZE, DEFAULT_CHUNK_OVERLAP)

for vol in [51, 52, 53]:
    name = f"Spurgeon_MTP_Vol{vol}.txt"
    path = os.path.join(output_dir, name)
    file_info = {"path": path, "name": name, "ext": "txt", "use_ocr": False}

    def report(stage, message, progress=None):
        print(f"  [{stage}] {message}")

    print(f"=== Vol{vol} ===")
    result = process_one_file(
        file_info, converter, splitter, output_dir,
        DEFAULT_CHUNK_SIZE, DEFAULT_CHUNK_OVERLAP,
        report=report, force_rechunk=True,
    )
    print(f"Vol{vol}: success={result['success']} failed_stage={result.get('failed_stage')} reason={result.get('reason')}")
    print(f"  metrics={result.get('metrics')}")
    print()
