#!/usr/bin/env python3
"""DBMA pipeline performance benchmark.

Usage:
  python scripts/benchmark_pipeline.py --input data/sample.txt --output output/bench
  python scripts/benchmark_pipeline.py --glob "data/**/*.txt" --limit 5
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics as stats
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.processing import build_converter, build_splitter, process_one_file


@dataclass
class BenchRow:
    file: str
    success: bool
    elapsed_sec: float
    chunks: int
    md_saved: str
    notes: str


def iter_files(args: argparse.Namespace) -> list[Path]:
    if args.input:
        return [Path(args.input)]
    if args.glob:
        return sorted(ROOT.glob(args.glob))[: args.limit]
    return []


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", help="single input file")
    parser.add_argument("--glob", help="glob pattern for multiple files")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--output", default="output/bench")
    # SPRINT 1 FIX: Use core.config defaults to prevent CRITICAL benchmark comparability issue.
    # Benchmark must use same chunk params as production pipeline (config.yaml source of truth).
    from core.config import DEFAULT_CHUNK_SIZE, DEFAULT_CHUNK_OVERLAP  # noqa: E402
    parser.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE,
                        help=f"Chunk size (default: {DEFAULT_CHUNK_SIZE} from config.yaml)")
    parser.add_argument("--chunk-overlap", type=int, default=DEFAULT_CHUNK_OVERLAP,
                        help=f"Chunk overlap (default: {DEFAULT_CHUNK_OVERLAP} from config.yaml)")
    args = parser.parse_args()

    files = iter_files(args)
    if not files:
        raise SystemExit("No input files found.")

    # 이미 처리되어 삭제된 파일 필터링
    existing_files = [f for f in files if f.exists()]
    skipped = [f for f in files if not f.exists()]
    if skipped:
        print(f"[WARN] 건너뛴 파일 (이미 처리됨): {[str(s) for s in skipped]}")
    files = existing_files
    if not files:
        raise SystemExit("처리할 원본 파일이 없습니다.")

    output_dir = (ROOT / args.output).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    converter = build_converter()
    splitter = build_splitter(args.chunk_size, args.chunk_overlap)

    rows: list[BenchRow] = []
    timings = []
    skipped_count = 0

    for fp in files:
        # 파일 존재 여부 재확인 (벤치마크 실행 중 삭제된 경우)
        if not fp.exists():
            print(f"[WARN] 파일 처리 건너뜀 (존재하지 않음): {fp}")
            skipped_count += 1
        file_info = {
            "path": str(fp),
            "name": fp.name,
            "ext": fp.suffix,
        }
        t0 = time.perf_counter()
        result = process_one_file(
            file_info=file_info,
            converter=converter,
            splitter=splitter,
            output_dir=str(output_dir),
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap,
        )
        logs = result.get("logs", [])
        success = result.get("success", False)
        elapsed = time.perf_counter() - t0
        timings.append(elapsed)

        chunk_count = 0
        md_saved = ""
        notes = "파일 존재하지 않음" if not fp.exists() else ""
        
        if not fp.exists():
            rows.append(BenchRow(file=str(fp), success=False, elapsed_sec=0, chunks=0, md_saved="", notes=notes))
            continue
        for item in logs:
            msg = item.get("msg", "") if isinstance(item, dict) else str(item)
            # 청크 수 추출: "청킹 완료: N chunks" 또는 "optimize_chunks 실행 완료: N chunks"
            if "청킹 완료:" in msg or "optimize_chunks 실행 완료" in msg:
                try:
                    chunk_count = int(msg.split(":")[-1].strip().split()[0])
                except Exception:
                    pass
            # Sprint 1: optimized MD is deprecated; canonical output is {stem}.md
            # Track canonical MD path instead of deprecated optimized MD
            if "MD 저장 완료:" in msg and "DEPRECATED" not in msg:
                md_saved = msg.split(":", 1)[-1].strip()
            if isinstance(item, dict) and item.get("cls") == "log-warn":
                notes = msg

        rows.append(
            BenchRow(
                file=str(fp),
                success=success,
                elapsed_sec=round(elapsed, 4),
                chunks=chunk_count,
                md_saved=md_saved,
                notes=notes,
            )
        )

    csv_path = output_dir / "benchmark_results.csv"
    json_path = output_dir / "benchmark_summary.json"

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(asdict(rows[0]).keys()))
        writer.writeheader()
        writer.writerows(asdict(r) for r in rows)

    summary = {
        "files": len(rows),
        "success_rate": round(sum(1 for r in rows if r.success) / len(rows), 4),
        "avg_elapsed_sec": round(stats.mean(timings), 4),
        "median_elapsed_sec": round(stats.median(timings), 4),
        "max_elapsed_sec": round(max(timings), 4),
        "min_elapsed_sec": round(min(timings), 4),
        "chunk_size": args.chunk_size,
        "chunk_overlap": args.chunk_overlap,
        "output_dir": str(output_dir),
    }

    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"CSV: {csv_path}")
    print(f"JSON: {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
