#!/usr/bin/env python3
"""scripts/j5_ingest_personal_library.py — 개인 서재 자료를 정식 경로로 편입한다 (J5).

[J5, 2026-10-18] 제품 조건 ②⑤ — 목회자의 교단·개인 신학이 반영된 답을 주려면
그의 자료가 코퍼스에 있어야 한다. 그런데 프로덕션 코퍼스 119,595건은 **한글
포함 청크가 0.00%**다(전부 19세기 영문 퍼블릭도메인). 한국어 자료가 이 앱의
파이프라인을 통과한 적이 한 번도 없다는 뜻이고, 그래서 ②⑤는 코드로 메울 수
없는 상태였다(`docs/NAE_ANSWER_QUALITY_JOURNEY_PLAN_v1.md` J5).

이 스크립트는 UI의 "내 자료" 편입 경로(`ui/pages/library.py:477`)와 **같은
함수**를 쓴다 — `process_one_file()` → registry 등록 → `reconcile_pending()`.
별도 ingest 경로를 만들지 않는다(ADR-001: Retrieval/Index Authority 우회 금지).

서지(title/author)는 **각 책 표제지에서 직접 확인한 값만** 사이드카로 넣는다.
추정·날조하지 않는다 — 확인되지 않은 책은 목록에 넣지 않고 건너뛴다.

사용:
    # 기본은 dry-run(무엇을 할지 출력만)
    python3 scripts/j5_ingest_personal_library.py
    python3 scripts/j5_ingest_personal_library.py --apply

**반드시 프로덕션 루트(`~/DBMA`)를 CWD로 두고 실행한다** — raw_dir/output_dir/
bench_dir가 모두 상대경로라 CWD 기준으로 해석된다. 워크트리에서 실행하면
워크트리의 빈 디렉터리에 쓴다.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import DEFAULT_OUTPUT_DIR, DEFAULT_RAW_DIR  # noqa: E402
from core.index_orchestrator import reconcile_pending  # noqa: E402
from core.processing import build_converter, build_splitter, process_one_file  # noqa: E402

# UI "내 자료" 편입과 같은 청킹 파라미터(ui/pages/library.py:477, CLAUDE.md 기준).
_CHUNK_SIZE = 1200
_CHUNK_OVERLAP = 200

# 편입 대상. title/author는 각 책 **표제지 실측**이다(2026-10-18 확인).
#
# 범위 결정(2026-10-18 사용자): 톰 라이트 "모든 사람을 위한" 시리즈 8종 중
# **복음서·사도행전 5종만** 편입하고 로마서 I부·고린도전서·고린도후서 3종은
# 보류한다. 라이트는 New Perspective on Paul의 대표 주자여서 칭의론이 사용자의
# 1689 런던신앙고백 계열 개혁파 침례교 입장과 갈리는데, 보류한 3종이 바로 그
# 교리의 본문(롬 1-8장, 고전후)이다. 코퍼스의 한글 비율이 0%인 상태에서 그
# 3종을 넣으면 한국어 칭의 질의가 사실상 전부 라이트의 근거로 답하게 된다.
# 복음서·행전 강해는 그 충돌 지점에서 멀고, 한국어 경로 전수 검증이라는 이번
# 목적은 5종으로 충분히 달성된다.
_SOURCES: list[dict[str, str]] = [
    {
        "src": "data/beta_corpus/bible_study/3. 마가복음.pdf",
        "title": "모든 사람을 위한 마가복음",
        "author": "톰 라이트",
    },
    {
        "src": "data/beta_corpus/bible_study/5. 요한복음1.pdf",
        "title": "모든 사람을 위한 요한복음 I부 (1-10장)",
        "author": "톰 라이트",
    },
    {
        "src": "data/beta_corpus/bible_study/6. 요한복음2.pdf",
        "title": "모든 사람을 위한 요한복음 II부 (11-21장)",
        "author": "톰 라이트",
    },
    {
        "src": "data/beta_corpus/bible_study/7. 사도행전1.pdf",
        "title": "모든 사람을 위한 사도행전 I부 (1-12장)",
        "author": "톰 라이트",
    },
    {
        "src": "data/beta_corpus/bible_study/8. 사도행전2.pdf",
        "title": "모든 사람을 위한 사도행전 II부 (13-28장)",
        "author": "톰 라이트",
    },
]


def _plan(raw_dir: str) -> list[dict[str, str]]:
    plan = []
    for entry in _SOURCES:
        src = Path(entry["src"])
        dest = Path(raw_dir) / src.name
        plan.append({
            **entry,
            "dest": str(dest),
            "exists_src": src.exists(),
            "exists_dest": dest.exists(),
        })
    return plan


def _write_sidecar(dest: Path, title: str, author: str) -> Path:
    """`data/RAW/<filename>.meta.json` — core/processing.py::resolve_title_author()가
    읽는 형식 그대로. 이 값이 registry를 거쳐 TSU 레코드의 title/author로
    전파된다(core/tsu_builder.py:383)."""
    meta_path = dest.parent / f"{dest.name}.meta.json"
    meta_path.write_text(
        json.dumps({"title": title, "author": author}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return meta_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="실제로 편입한다 (기본: dry-run)")
    parser.add_argument("--raw-dir", default=DEFAULT_RAW_DIR)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    plan = _plan(args.raw_dir)
    print(f"[J5] 편입 대상 {len(plan)}건 · raw_dir={args.raw_dir} · output_dir={args.output_dir}")
    missing = [p for p in plan if not p["exists_src"]]
    for p in plan:
        mark = "!" if not p["exists_src"] else ("~" if p["exists_dest"] else "+")
        print(f"  [{mark}] {Path(p['src']).name} → {p['title']} / {p['author']}")
    if missing:
        print(f"\n원본 {len(missing)}건을 찾을 수 없다 — 중단한다(부분 편입은 하지 않는다).")
        return 1
    if not args.apply:
        print("\n(dry-run — 실제로 편입하려면 --apply)")
        return 0

    converter = build_converter(use_ocr=False)
    splitter = build_splitter(chunk_size=_CHUNK_SIZE, chunk_overlap=_CHUNK_OVERLAP)

    results = []
    for p in plan:
        dest = Path(p["dest"])
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.exists():
            shutil.copy2(p["src"], dest)
        meta_path = _write_sidecar(dest, p["title"], p["author"])
        print(f"\n[J5] 처리 시작: {dest.name} (사이드카 {meta_path.name})", flush=True)

        file_info = {
            "name": dest.name,
            "path": str(dest),
            "size": dest.stat().st_size,
            "ext": dest.suffix.lstrip("."),
        }
        result = process_one_file(
            file_info, converter, splitter, args.output_dir, _CHUNK_SIZE, _CHUNK_OVERLAP
        )
        ok = bool(result.get("success"))
        print(f"[J5] {'성공' if ok else '실패'}: {dest.name}"
              f" — {result.get('reason') or result.get('chunks', '')}", flush=True)
        results.append({"name": dest.name, "success": ok, "detail": result})

    print("\n[J5] registry → TSU 반영(reconcile_pending)", flush=True)
    rec = reconcile_pending(args.output_dir)
    print(f"[J5] pending={rec.get('pending')} reconciled={rec.get('reconciled')}"
          f" purged={rec.get('purged')} failed={rec.get('failed')}")

    ok_n = sum(1 for r in results if r["success"])
    print(f"\n[J5] 완료 — 처리 성공 {ok_n}/{len(results)}건")
    return 0 if ok_n == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
