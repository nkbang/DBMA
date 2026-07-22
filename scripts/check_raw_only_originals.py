#!/usr/bin/env python
"""scripts/check_raw_only_originals.py — RAW에는 없고 data/제련완성본에만
남아있는 원본 파일을 찾아 경고한다 (2026-07-21).

배경: core/processing.py::copy_source_file()은 RAW 원본을 절대 옮기거나
지우지 않는다("Sprint 2 policy: Original research documents must NEVER
be moved or deleted") — 처리 시 output 디렉터리로 복사만 한다. 그런데
사용자가 처리 후 RAW에서 원본을 수동으로 지우는 경우가 있어, 일부
문서는 output(data/제련완성본)이 유일한 원본 보관소가 돼 버린다.
output 디렉터리는 "재생성 가능한 처리 결과물"이라는 전제로 취급되기
쉬워서, 이 상태를 모른 채 output을 정리하면 해당 문서가 영구
소실된다(실측: 2026-07-21, 14개 파일이 이 상태였음).

읽기 전용 — 아무것도 지우거나 옮기지 않는다. output 디렉터리 관련
정리 작업(cleanup_duplicate_outputs.py 실행, 전체 재처리 등) 전에
항상 먼저 실행할 것을 권장한다.

Usage:
    python scripts/check_raw_only_originals.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

RAW_DIR = Path("data/RAW")
OUTPUT_DIR = Path("data/제련완성본")
BATCH_STATE_PATH = OUTPUT_DIR / ".batch_state.json"


def find_output_only_originals() -> list[str]:
    """.batch_state.json의 processed(원본 파일명) 목록 중 RAW에 없는
    것을 반환한다. RAW 원본이 이미 존재하는 파일은 제외."""
    if not BATCH_STATE_PATH.exists():
        return []
    state = json.loads(BATCH_STATE_PATH.read_text(encoding="utf-8"))
    processed = state.get("processed", [])

    raw_files = set(os.listdir(RAW_DIR)) if RAW_DIR.exists() else set()

    return sorted(p for p in processed if p not in raw_files)


def main() -> None:
    only_in_output = find_output_only_originals()

    print("=" * 70)
    print("RAW에는 없고 output(data/제련완성본)에만 원본이 존재하는 파일")
    print("=" * 70)
    if not only_in_output:
        print("  없음 — 모든 처리된 원본이 RAW에도 존재합니다.")
        return

    for name in only_in_output:
        print(f"  ⚠️  {name}")

    print()
    print(f"총 {len(only_in_output)}개 — 이 파일들은 output 디렉터리가 유일한 원본 보관소입니다.")
    print("output 디렉터리를 정리/삭제/전체 재처리하기 전에, 이 목록을 먼저")
    print("RAW 또는 별도 백업 위치로 복사해 두십시오 (삭제 아님, 복사).")


if __name__ == "__main__":
    main()
