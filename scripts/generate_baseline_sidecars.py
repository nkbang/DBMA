"""scripts/generate_baseline_sidecars.py — 기존 67종 베이스라인 코퍼스에
사이드카 메타데이터(`.meta.json`)를 생성한다.

배경: 베이스라인 코퍼스는 ~/NAE_CORPUS_RAW/raw/archive_org/sermons/<dir>/ocr.txt
에서 만든 순수 텍스트로 적재돼 있어, PDF 자체에 있는 title/author가
파이프라인에 전달되지 않는다(txt 추출기는 내장 메타데이터가 없음).
같은 디렉터리의 original.pdf에는 Google Books / Internet Archive가 넣은
실제 title/author가 종종 남아 있다 — `pdfinfo`로 이를 읽어 사이드카로
옮긴다(추정·날조 없음, 실제 PDF 문서 정보 그대로 사용).

PDF에 title/author가 전혀 없거나(core/processing.py의 D-3 휴리스틱으로
"신뢰 불가" 판정된) 경우, 임의로 추정하지 않고 건너뛴다 — 단, 같은
시리즈(Spurgeon MTP 51/52권)에서 나머지 25권 전부가 동일 저자/제목으로
확인된 경우에 한해 _KNOWN_SERIES_FALLBACK으로 명시적으로 채운다(추정이
아니라 같은 코퍼스 내 25건의 실측 확인 결과를 그대로 적용).

사용:
    python3 scripts/generate_baseline_sidecars.py [--apply]

기본은 dry-run(무엇을 쓸지 출력만). --apply를 줘야 실제로
data/RAW/<filename>.meta.json을 쓴다.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.processing import _is_untrustworthy_embedded_value  # noqa: E402

MANIFEST_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "scripts",
    "baseline_corpus_manifest.json",
)
RAW_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "RAW")

# [백필 전용] 같은 시리즈 25권에서 실측 확인된 저자/제목을 PDF 메타데이터가
# 없는 2권(Vol51/52)·저자 누락 2권(Vol12/Vol30)에만 적용한다. 추정이 아니라
# 동일 코퍼스 내 다른 권들의 실제 pdfinfo 결과를 근거로 한다.
_KNOWN_SERIES_FALLBACK = {
    "Spurgeon_MTP_Vol12": {"author": "C. H. Spurgeon"},
    "Spurgeon_MTP_Vol30": {"author": "C. H. Spurgeon"},
    "Spurgeon_MTP_Vol51": {"title": "The Metropolitan Tabernacle Pulpit", "author": "C. H. Spurgeon"},
    "Spurgeon_MTP_Vol52": {"title": "The Metropolitan Tabernacle Pulpit", "author": "C. H. Spurgeon"},
}


def _pdfinfo_title_author(pdf_path: str) -> tuple:
    out = subprocess.run(["pdfinfo", pdf_path], capture_output=True, text=True, timeout=30).stdout
    title = author = None
    for line in out.splitlines():
        if line.startswith("Title:"):
            title = line.split(":", 1)[1].strip() or None
        elif line.startswith("Author:"):
            author = line.split(":", 1)[1].strip() or None
    return title, author


def build_sidecar_entries(source_root: str) -> "tuple[list, list]":
    """반환: (written_entries, skipped) — written_entries는
    [(filename, {"title":..., "author":...})], skipped는 [(source_dir, reason)]."""
    manifest = json.load(open(MANIFEST_PATH, "r", encoding="utf-8"))
    written = []
    skipped = []
    for entry in manifest["entries"]:
        filename = entry["filename"]
        source_dir = entry["source_dir"]
        pdf_path = os.path.join(source_root, source_dir, "original.pdf")
        if not os.path.isfile(pdf_path):
            skipped.append((source_dir, "original.pdf 없음"))
            continue

        title, author = _pdfinfo_title_author(pdf_path)
        if title and _is_untrustworthy_embedded_value(title):
            title = None
        if author and _is_untrustworthy_embedded_value(author):
            author = None

        fallback = _KNOWN_SERIES_FALLBACK.get(source_dir, {})
        if title is None:
            title = fallback.get("title")
        if author is None:
            author = fallback.get("author")

        if title is None and author is None:
            skipped.append((source_dir, "title/author 둘 다 확인 불가 — 추정 없이 건너뜀"))
            continue

        sidecar = {}
        if title:
            sidecar["title"] = title
        if author:
            sidecar["author"] = author
        written.append((filename, sidecar))
    return written, skipped


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="실제로 .meta.json 파일을 쓴다 (기본: dry-run)")
    parser.add_argument(
        "--source-root",
        default=os.path.expanduser("~/NAE_CORPUS_RAW/raw/archive_org/sermons"),
        help="original.pdf가 있는 원본 디렉터리 루트",
    )
    parser.add_argument(
        "--raw-dir",
        default=RAW_DIR,
        help="사이드카(.meta.json)를 쓸 data/RAW 경로 (기본: 이 스크립트 기준 data/RAW)",
    )
    args = parser.parse_args()

    written, skipped = build_sidecar_entries(args.source_root)

    print(f"작성 대상: {len(written)}건, 건너뜀: {len(skipped)}건\n")
    for filename, sidecar in written:
        print(f"  [W] {filename} -> {sidecar}")
    for source_dir, reason in skipped:
        print(f"  [S] {source_dir}: {reason}")

    if not args.apply:
        print("\n(dry-run — 실제로 쓰려면 --apply)")
        return 0

    os.makedirs(args.raw_dir, exist_ok=True)
    for filename, sidecar in written:
        meta_path = os.path.join(args.raw_dir, f"{filename}.meta.json")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(sidecar, f, ensure_ascii=False, indent=2)
    print(f"\n{len(written)}건 사이드카 작성 완료 → {args.raw_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
