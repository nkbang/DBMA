"""TSU 데이터셋의 verse_mapping이 실제 저장된 content로 재파싱했을 때도
재현되는지 전수 감사한다. 읽기 전용 — 아무 파일도 수정하지 않는다.

배경: "TSU-ROM-...chunk_00293" 레코드에서 verse_mapping이
{book_id: ROM, chapter: 8, verse_start: 58}인데, 저장된 content를
QueryParser로 재파싱하면 JHN(요한복음) 참조만 나오고 ROM은 전혀
나오지 않는 불일치를 발견(2026-07-27, ADR-010 Phase 2 베이스라인
측정 중 실측). 이 불일치가 이 레코드 하나만의 문제인지, 파이프라인
전체의 구조적 문제인지 규모를 먼저 파악한다.

Usage:
    python scripts/audit_verse_mapping_consistency.py [--limit N]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.config import DEFAULT_TSU_DATASET_PATH
from core.retrieval import QueryParser


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="검사할 레코드 수 제한(디버그용)")
    args = parser.parse_args()

    qp = QueryParser()

    total = 0
    has_verse_mapping = 0
    matched = 0
    mismatched = 0
    no_refs_found = 0
    mismatch_examples: list[dict] = []

    with open(DEFAULT_TSU_DATASET_PATH, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if args.limit and i >= args.limit:
                break
            total += 1
            record = json.loads(line)
            vm = record.get("verse_mapping")
            if not vm or not vm.get("book_id") or not vm.get("chapter"):
                continue
            has_verse_mapping += 1

            content = record.get("content", "")
            refs = qp.parse(content).scripture_refs

            if not refs:
                no_refs_found += 1
                mismatched += 1
                if len(mismatch_examples) < 20:
                    mismatch_examples.append({
                        "tsu_id": record.get("tsu_id"),
                        "stored": vm,
                        "reparsed": [],
                        "reason": "저장된 content에서 참조 자체를 못 찾음",
                    })
                continue

            found = any(
                r.book_id == vm.get("book_id")
                and r.chapter == vm.get("chapter")
                and (vm.get("verse_start") is None or r.verse_start == vm.get("verse_start"))
                for r in refs
            )
            if found:
                matched += 1
            else:
                mismatched += 1
                if len(mismatch_examples) < 20:
                    mismatch_examples.append({
                        "tsu_id": record.get("tsu_id"),
                        "stored": vm,
                        "reparsed": [
                            {"book_id": r.book_id, "chapter": r.chapter, "verse_start": r.verse_start}
                            for r in refs
                        ],
                        "reason": "재파싱 결과에 저장된 book_id/chapter/verse_start 조합 없음",
                    })

            if i % 5000 == 0 and i > 0:
                print(f"  ...{i}건 처리, 현재까지 mismatch={mismatched}/{has_verse_mapping}", flush=True)

    print()
    print(f"=== 전체 레코드: {total} ===")
    print(f"verse_mapping 보유: {has_verse_mapping}")
    print(f"일치(matched): {matched}")
    print(f"불일치(mismatched): {mismatched} ({100*mismatched/has_verse_mapping:.2f}%)" if has_verse_mapping else "")
    print(f"  - 그중 참조 자체 미검출: {no_refs_found}")
    print()
    print("=== 불일치 샘플 (최대 20건) ===")
    for ex in mismatch_examples:
        print(json.dumps(ex, ensure_ascii=False))


if __name__ == "__main__":
    main()
