"""Chunk Summary Report — 파일별/유형별(doc_type) 청킹 결과 요약.

registry(data/제련완성본/registry/documents.json)에 이미 저장된
chunk_count/noise_score/doc_type만 읽는다 — 재청킹이나 Ollama 호출
없음, 읽기 전용, 순수 집계.

noise_label()(core/utils.py, 기존 함수 재사용)의 3단계(양호/주의/높음)
기준을 그대로 쓴다 — 새 기준을 만들지 않는다.

Usage:
    python scripts/report_chunk_summary.py [--csv]
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.config import DEFAULT_REGISTRY_PATH
from core.utils import noise_label

OUTPUT_DIR = Path("output/reports")


def load_processed_documents() -> list[dict]:
    registry = json.loads(Path(DEFAULT_REGISTRY_PATH).read_text(encoding="utf-8"))
    docs = registry.get("documents", {})
    return [v for v in docs.values() if v.get("status") == "processed"]


def build_per_file_rows(docs: list[dict]) -> list[dict]:
    rows = []
    for d in docs:
        noise = d.get("noise_score")
        rows.append({
            "source_file": d.get("source_file", ""),
            "doc_type": d.get("doc_type", "?"),
            "chunk_count": d.get("chunk_count", 0),
            "noise_score": noise,
            "noise_label": noise_label(noise) if noise is not None else "?",
            "is_ocr": d.get("is_ocr", False),
            "language": d.get("language", "?"),
        })
    rows.sort(key=lambda r: (r["doc_type"], r["source_file"]))
    return rows


def build_by_doctype_summary(rows: list[dict]) -> list[dict]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        groups[r["doc_type"]].append(r)

    summary = []
    for doc_type, group in sorted(groups.items()):
        noise_scores = [r["noise_score"] for r in group if r["noise_score"] is not None]
        chunk_counts = [r["chunk_count"] for r in group]
        high_noise_count = sum(1 for r in group if r["noise_label"] == "높음")
        summary.append({
            "doc_type": doc_type,
            "문서수": len(group),
            "평균_chunk_count": round(sum(chunk_counts) / len(chunk_counts), 1) if chunk_counts else 0,
            "평균_noise_score": round(sum(noise_scores) / len(noise_scores), 1) if noise_scores else None,
            "노이즈_높음_비율": f"{100 * high_noise_count / len(group):.1f}%" if group else "0%",
        })
    return summary


def print_report(per_file: list[dict], by_type: list[dict]) -> None:
    print("=== 유형별(doc_type) 요약 ===")
    print(f"{'doc_type':<12} {'문서수':>6} {'평균chunk':>10} {'평균noise':>10} {'높음비율':>8}")
    for row in by_type:
        avg_noise = f"{row['평균_noise_score']:.1f}" if row["평균_noise_score"] is not None else "-"
        print(f"{row['doc_type']:<12} {row['문서수']:>6} {row['평균_chunk_count']:>10} {avg_noise:>10} {row['노이즈_높음_비율']:>8}")

    print()
    print(f"=== 파일별 상세 ({len(per_file)}건) ===")
    print(f"{'doc_type':<10} {'chunks':>7} {'noise':>7} {'label':<6} {'ocr':<5} {'source_file'}")
    for row in per_file:
        noise = f"{row['noise_score']:.1f}" if row["noise_score"] is not None else "-"
        print(
            f"{row['doc_type']:<10} {row['chunk_count']:>7} {noise:>7} "
            f"{row['noise_label']:<6} {str(row['is_ocr']):<5} {row['source_file']}"
        )


def write_csv(per_file: list[dict], by_type: list[dict]) -> tuple[Path, Path]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    per_file_path = OUTPUT_DIR / "chunk_summary_by_file.csv"
    by_type_path = OUTPUT_DIR / "chunk_summary_by_doctype.csv"

    with per_file_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(per_file[0].keys()))
        writer.writeheader()
        writer.writerows(per_file)

    with by_type_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(by_type[0].keys()))
        writer.writeheader()
        writer.writerows(by_type)

    return per_file_path, by_type_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Chunk Summary Report")
    parser.add_argument("--csv", action="store_true", help="output/reports/에 CSV로도 저장")
    args = parser.parse_args()

    docs = load_processed_documents()
    per_file = build_per_file_rows(docs)
    by_type = build_by_doctype_summary(per_file)

    print_report(per_file, by_type)

    if args.csv:
        p1, p2 = write_csv(per_file, by_type)
        print()
        print(f"CSV 저장: {p1}")
        print(f"CSV 저장: {p2}")


if __name__ == "__main__":
    main()
