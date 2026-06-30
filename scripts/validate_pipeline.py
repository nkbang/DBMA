#!/usr/bin/env python3
"""DBMA validation runner.

Runs:
1. pytest for functional verification
2. benchmark for performance verification

Usage:
  python3 scripts/validate_pipeline.py
  python3 scripts/validate_pipeline.py --skip-benchmark
  python3 scripts/validate_pipeline.py --pytest-args "-q"
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable or "python3"


def run_command(cmd: list[str], label: str) -> int:
    print(f"\n=== {label} ===")
    print(" ".join(cmd))
    proc = subprocess.run(cmd, cwd=ROOT)
    return proc.returncode


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-benchmark", action="store_true")
    parser.add_argument("--pytest-args", default="-v --tb=short")
    parser.add_argument("--benchmark-glob", default="data/**/*.pdf")
    parser.add_argument("--benchmark-limit", type=int, default=5)
    parser.add_argument("--benchmark-output", default="output/bench")
    parser.add_argument("--chunk-size", type=int, default=1000)
    parser.add_argument("--chunk-overlap", type=int, default=120)
    args = parser.parse_args()

    pytest_cmd = [
        PYTHON,
        "-m",
        "pytest",
        "tests/",
        *args.pytest_args.split(),
    ]
    rc = run_command(pytest_cmd, "PYTEST")

    if rc != 0:
        print("\nValidation failed at pytest stage.")
        return rc

    if args.skip_benchmark:
        print("\nBenchmark skipped.")
        return 0

    benchmark_cmd = [
        PYTHON,
        "scripts/benchmark_pipeline.py",
        "--glob",
        args.benchmark_glob,
        "--limit",
        str(args.benchmark_limit),
        "--output",
        args.benchmark_output,
        "--chunk-size",
        str(args.chunk_size),
        "--chunk-overlap",
        str(args.chunk_overlap),
    ]
    rc = run_command(benchmark_cmd, "BENCHMARK")

    if rc != 0:
        print("\nValidation failed at benchmark stage.")
        return rc

    print("\nValidation completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
