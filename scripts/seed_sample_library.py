"""scripts/seed_sample_library.py — DBMA-UX-003 Sample Library 시딩.

`scripts/sample_library_content/*.md`(신학적으로 정확한 샘플 연구 3건,
Design Brief §4.1 기반)을 DEFAULT_RAW_DIR로 복사하고 실제 처리
파이프라인(core.processing.process_one_file)으로 처리한 뒤, 그
document_id 목록을 DEFAULT_SAMPLE_LIBRARY_PATH에 기록한다.
ui/pages/library.py가 이 파일을 읽어 "기본 자료(읽기 전용)" 섹션을
표시한다.

멱등성: 이미 처리된 샘플은 건너뛴다(content hash 기반 document_id가
동일하면 재처리하지 않음). 여러 번 실행해도 안전하다.

사용법:
    /Users/David/envs/dbma311/bin/python scripts/seed_sample_library.py
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.config import DEFAULT_RAW_DIR, DEFAULT_OUTPUT_DIR, DEFAULT_SAMPLE_LIBRARY_PATH
from core.processing import build_converter, build_splitter, process_one_file

CONTENT_DIR = Path(__file__).resolve().parent / "sample_library_content"


def main() -> None:
    if not CONTENT_DIR.exists():
        print(f"샘플 원문 폴더가 없습니다: {CONTENT_DIR}")
        return

    raw_dir = Path(DEFAULT_RAW_DIR)
    raw_dir.mkdir(parents=True, exist_ok=True)

    converter = build_converter(use_ocr=False)
    splitter = build_splitter(chunk_size=1200, chunk_overlap=200)

    sample_ids: list[str] = []
    if os.path.exists(DEFAULT_SAMPLE_LIBRARY_PATH):
        with open(DEFAULT_SAMPLE_LIBRARY_PATH, "r", encoding="utf-8") as f:
            sample_ids = json.load(f).get("document_ids", [])

    for src in sorted(CONTENT_DIR.glob("*.md")):
        dest = raw_dir / src.name
        if not dest.exists():
            shutil.copy2(src, dest)

        file_info = {
            "name": src.name,
            "path": str(dest),
            "size": dest.stat().st_size,
            "ext": "md",
        }
        result = process_one_file(file_info, converter, splitter, DEFAULT_OUTPUT_DIR, 1200, 200)
        if not result["success"]:
            print(f"실패: {src.name} — {result.get('reason')}")
            continue

        doc_id = result["metrics"].get("document_id")
        print(f"완료: {src.name} -> {doc_id}")
        if doc_id and doc_id not in sample_ids:
            sample_ids.append(doc_id)

    os.makedirs(os.path.dirname(DEFAULT_SAMPLE_LIBRARY_PATH), exist_ok=True)
    with open(DEFAULT_SAMPLE_LIBRARY_PATH, "w", encoding="utf-8") as f:
        json.dump({"document_ids": sample_ids}, f, ensure_ascii=False, indent=2)

    print(f"\n샘플 라이브러리 등록 완료: {len(sample_ids)}건 -> {DEFAULT_SAMPLE_LIBRARY_PATH}")


if __name__ == "__main__":
    main()
