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
    parser.add_argument("--chunk-size", type=int, default=1000)
    parser.add_argument("--chunk-overlap", type=int, default=120)
    args = parser.parse_args()

    files = iter_files(args)
    if not files:
        raise SystemExit("No input files found.")

    output_dir = (ROOT / args.output).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    converter = build_converter()
    splitter = build_splitter(args.chunk_size, args.chunk_overlap)

    rows: list[BenchRow] = []
    timings = []

    for fp in files:
        file_info = {
            "path": str(fp),
            "name": fp.name,
            "ext": fp.suffix,
        }
        t0 = time.perf_counter()
        logs, success = process_one_file(
            file_info=file_info,
            converter=converter,
            splitter=splitter,
            output_dir=str(output_dir),
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap,
        )
        elapsed = time.perf_counter() - t0
        timings.append(elapsed)

        chunk_count = 0
        md_saved = ""
        notes = ""
        for item in logs:
            msg = item.get("msg", "") if isinstance(item, dict) else str(item)
            if "옵티마이저 실행 완료" in msg:
                try:
                    chunk_count = int(msg.split(":")[-1].strip().split()[0])
                except Exception:
                    pass
            if "최적화 MD 저장 완료" in msg:
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
