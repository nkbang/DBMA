#!/usr/bin/env python
"""scripts/cleanup_duplicate_outputs.py — data/제련완성본 중복/고아 산출물 정리
(C1-TASK-ORDER-006 반려 사유 반영, CUE 직접 구현, 2026-07-21).

두 가지 다른 패턴을 분리해서 판별한다 (하나의 "그룹화" 로직으로
뭉뚱그리지 않음 — 원래 C1 계획의 반려 사유):

1. Orphan (미완성 산출물): {stem}_pdf.md는 있는데 chunks.txt/
   chunks_meta.json이 없고, 이미 완전히 처리된 비-clearscan 원본이
   따로 존재하는 경우. 판별 기준은 파일 크기가 아니라 "chunks 파일
   존재 여부"다.
2. 진짜 중복 업로드: 두 개 이상의 원본 .pdf 파일 크기(바이트)가
   완전히 일치하고, 각각 완전한 처리 세트(.md+chunks.txt+
   chunks_meta.json)를 가진 경우.

기본은 dry-run(목록만 출력) — 실제 삭제는 --execute 플래그가 있어야
하고, 그 전에 반드시 backups/cleanup_duplicate_outputs_{timestamp}/로
실제 파일을 복사한다. .batch_state.json의 processed 목록도 삭제와
같은 실행 안에서 동기화한다.

Usage:
    python scripts/cleanup_duplicate_outputs.py              # dry-run
    python scripts/cleanup_duplicate_outputs.py --execute     # 실제 삭제 (백업 후)
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

OUTPUT_DIR = Path("data/제련완성본")
BATCH_STATE_PATH = OUTPUT_DIR / ".batch_state.json"
TSU_DATASET_PATH = Path("output/bench/tsu_dataset.jsonl")
BACKUP_ROOT = Path("backups")


def _load_batch_state() -> dict:
    if BATCH_STATE_PATH.exists():
        return json.loads(BATCH_STATE_PATH.read_text(encoding="utf-8"))
    return {"processed": [], "timestamp": ""}


def find_orphans() -> list[dict]:
    """chunks.txt/chunks_meta.json이 없는 *_pdf.md 중, 같은 이름에서
    "clearscan_cropped" 등 접미사를 뗀 완전 처리된 원본이 이미 있는
    경우만 orphan으로 판별. RAW 원본이 없는 채로 유일한 소스인 경우
    (예: 로마서2clearscan_cropped)는 chunks.txt/meta가 정상적으로
    있으므로 이 조건에서 자동으로 제외된다."""
    orphans = []
    for md_path in sorted(OUTPUT_DIR.glob("*_pdf.md")):
        stem = md_path.stem  # "...{name}_pdf"
        chunks_txt = md_path.with_name(f"{stem}_chunks.txt")
        chunks_meta = md_path.with_name(f"{stem}_chunks_meta.json")
        if chunks_txt.exists() and chunks_meta.exists():
            continue  # 완전한 산출물 — orphan 아님
        orphans.append({
            "md": md_path,
            "reason": "chunks.txt/chunks_meta.json 없음 (미완성 산출물)",
        })
    return orphans


def find_size_duplicates() -> list[dict]:
    """원본 .pdf 파일 크기가 완전히 일치하는 쌍을 찾는다. 둘 다 완전한
    처리 세트(.md+chunks.txt+chunks_meta.json)를 갖춰야 "진짜 중복"으로
    카운트한다 — 한쪽만 처리된 경우는 다른 문제(미처리 대기)이지
    중복 정리 대상이 아니다."""
    by_size: dict[int, list[Path]] = {}
    for pdf_path in OUTPUT_DIR.glob("*.pdf"):
        size = pdf_path.stat().st_size
        by_size.setdefault(size, []).append(pdf_path)

    dup_groups = []
    for size, paths in by_size.items():
        if len(paths) < 2:
            continue
        complete = []
        for p in paths:
            stem = f"{p.stem}_pdf"
            md = p.with_name(f"{stem}.md")
            chunks_txt = p.with_name(f"{stem}_chunks.txt")
            chunks_meta = p.with_name(f"{stem}_chunks_meta.json")
            if md.exists() and chunks_txt.exists() and chunks_meta.exists():
                complete.append(p)
        if len(complete) >= 2:
            dup_groups.append({"size": size, "pdfs": complete})
    return dup_groups


_COPY_MARKERS = ("복사본", "copy", " copy", "(1)", "(2)")


def _pick_duplicate_keep_and_remove(pdfs: list[Path]) -> tuple[Path, list[Path]]:
    """중복 그룹에서 남길 것 하나를 고른다.

    [버그 수정, 2026-07-21] 원래는 ".batch_state.json에 있는 쪽을
    canonical로 취급"하려 했으나, 실측 결과 두 중복 파일 모두 별도로
    업로드·처리돼 둘 다 processed 목록에 있는 게 정상 상태였다
    (tracked 개수가 항상 1이 되는 전제가 틀림) — 그 결과 사전순
    폴백으로 떨어졌고, "7. 사도행전1 복사본.pdf"의 공백(0x20)이
    "7. 사도행전1.pdf"의 마침표(0x2E)보다 ASCII상 앞서 KEEP/REMOVE가
    뒤바뀌는 실제 오류가 dry-run에서 확인됐다.

    수정: "복사본"/"copy"/"(1)"/"(2)" 등 사본을 암시하는 표식이 없는
    파일명을 우선 남긴다. 그래도 동률이면(둘 다 표식 없음/있음)
    파일명이 짧은 쪽, 그래도 동률이면 사전순 — 항상 결정적."""
    def _copy_score(p: Path) -> tuple[int, int, str]:
        has_marker = any(m in p.name for m in _COPY_MARKERS)
        return (1 if has_marker else 0, len(p.name), p.name)

    keep = sorted(pdfs, key=_copy_score)[0]
    remove = [p for p in pdfs if p != keep]
    return keep, remove


def _sibling_files(pdf_path: Path) -> list[Path]:
    stem = f"{pdf_path.stem}_pdf"
    return [
        pdf_path,
        pdf_path.with_name(f"{stem}.md"),
        pdf_path.with_name(f"{stem}_chunks.txt"),
        pdf_path.with_name(f"{stem}_chunks_meta.json"),
    ]


def check_tsu_duplicates(remove_pdf_names: list[str]) -> list[str]:
    """TSU dataset에 삭제 대상 원본의 source_file 레코드가 있는지
    확인만 한다 — 실제 정리(레코드 제거)는 이 스크립트 범위 밖,
    CUE 별도 승인 필요(Task Order 006 §2-(3))."""
    if not TSU_DATASET_PATH.exists():
        return []
    found = []
    with open(TSU_DATASET_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            sf = rec.get("source_file", "")
            if sf in remove_pdf_names:
                found.append(sf)
    return sorted(set(found))


def plan() -> dict:
    orphans = find_orphans()
    dup_groups = find_size_duplicates()

    duplicate_removals = []
    for g in dup_groups:
        keep, remove = _pick_duplicate_keep_and_remove(g["pdfs"])
        duplicate_removals.append({"size": g["size"], "keep": keep, "remove": remove})

    remove_pdf_names = [p.name for d in duplicate_removals for p in d["remove"]]
    tsu_hits = check_tsu_duplicates(remove_pdf_names)

    return {"orphans": orphans, "duplicate_removals": duplicate_removals, "tsu_hits": tsu_hits}


def print_plan(p: dict) -> None:
    print("=" * 70)
    print("Orphan (미완성 산출물) — 삭제 대상 .md 단일 파일")
    print("=" * 70)
    if not p["orphans"]:
        print("  (없음)")
    for o in p["orphans"]:
        print(f"  - {o['md'].name}  [{o['reason']}]")

    print()
    print("=" * 70)
    print("진짜 중복 업로드 — 원본.pdf + .md + chunks.txt + chunks_meta.json 4종 세트")
    print("=" * 70)
    if not p["duplicate_removals"]:
        print("  (없음)")
    for d in p["duplicate_removals"]:
        print(f"  size={d['size']} bytes")
        print(f"    KEEP  : {d['keep'].name}")
        for r in d["remove"]:
            print(f"    REMOVE: {r.name} (+ .md/chunks.txt/chunks_meta.json)")

    print()
    print("=" * 70)
    print("TSU dataset(output/bench/tsu_dataset.jsonl) 중복 콘텐츠 확인")
    print("=" * 70)
    if p["tsu_hits"]:
        print("  ⚠️  다음 source_file이 TSU dataset에도 레코드가 있음 — 파일만")
        print("      지우면 검색 결과에는 중복이 남는다. 별도 CUE 승인 후 처리 필요:")
        for sf in p["tsu_hits"]:
            print(f"    - {sf}")
    else:
        print("  삭제 대상 원본의 TSU 레코드 없음 — 파일 삭제만으로 충분")

    total_files = len(p["orphans"]) + sum(len(d["remove"]) * 4 for d in p["duplicate_removals"])
    print()
    print(f"총 삭제 대상 파일 수(추정): {total_files}")


def execute(p: dict) -> None:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = BACKUP_ROOT / f"cleanup_duplicate_outputs_{timestamp}"
    backup_dir.mkdir(parents=True, exist_ok=True)

    to_delete: list[Path] = [o["md"] for o in p["orphans"]]
    remove_pdf_names_for_state: list[str] = []
    for d in p["duplicate_removals"]:
        for pdf in d["remove"]:
            to_delete.extend(_sibling_files(pdf))
            remove_pdf_names_for_state.append(pdf.name)

    for f in to_delete:
        if not f.exists():
            continue
        dest = backup_dir / f.name
        shutil.copy2(f, dest)

    for f in to_delete:
        if f.exists():
            f.unlink()

    if remove_pdf_names_for_state:
        state = _load_batch_state()
        processed = state.get("processed", [])
        state["processed"] = [n for n in processed if n not in remove_pdf_names_for_state]
        state["timestamp"] = datetime.now().isoformat()
        BATCH_STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"백업 위치: {backup_dir}")
    print(f"삭제된 파일 수: {len([f for f in to_delete])}")
    print(f".batch_state.json에서 제거된 항목: {remove_pdf_names_for_state}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true", help="실제 삭제 실행 (기본은 dry-run)")
    args = parser.parse_args()

    p = plan()
    print_plan(p)

    if args.execute:
        print()
        print("=" * 70)
        print("실행 모드 — 백업 후 삭제를 진행합니다.")
        print("=" * 70)
        execute(p)
    else:
        print()
        print("(dry-run — 실제 삭제하려면 --execute 플래그로 다시 실행하세요)")


if __name__ == "__main__":
    main()
