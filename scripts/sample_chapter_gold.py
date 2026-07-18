#!/usr/bin/env python3
"""scripts/sample_chapter_gold.py — Stratified, reproducible sample of the
chapter-level gold standard for smoke benchmarks.

SPRINT21-E: replaces systematic "every Nth query" sampling (which risked
periodic position bias against a gold standard laid out in per-book/
per-chapter blocks — observed as a 150-query systematic sample reading
P@1=0.38 against a full-set baseline of P@1=0.242) with a fixed-seed
stratified-by-book random sample, so a smoke run correlates with the full
1500-query benchmark instead of reflecting sampling artifacts.

Usage:
    python -m scripts.sample_chapter_gold --fraction 0.1
    python -m scripts.sample_chapter_gold --fraction 0.1 --seed 42 \
        --gold-path output/bench/chapter_level_gold_standard_v1.json \
        --out /tmp/chapter_sample.json
"""

from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Any


def stratified_sample(
    queries: list[dict[str, Any]],
    fraction: float,
    seed: int = 42,
) -> list[dict[str, Any]]:
    """Sample `fraction` of queries from each expected_book_id group
    independently, so the sample's book distribution matches the full
    set's proportionally (unlike systematic/every-Nth sampling, which can
    align with periodic structure in the gold standard's generation order
    — e.g. queries grouped in fixed-size blocks per chapter/intent).

    Deterministic: same (queries, fraction, seed) always produces the same
    sample, so smoke runs are comparable across time/machines.
    """
    by_book: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for q in queries:
        by_book[q.get("expected_book_id", "UNKNOWN")].append(q)

    rng = random.Random(seed)
    sample: list[dict[str, Any]] = []
    for book_id in sorted(by_book):  # deterministic iteration order
        group = by_book[book_id]
        k = max(1, round(len(group) * fraction))
        sample.extend(rng.sample(group, min(k, len(group))))

    # Stable overall order: sort by original id.
    sample.sort(key=lambda q: q.get("id", ""))
    return sample


def main() -> None:
    parser = argparse.ArgumentParser(description="Stratified, reproducible chapter-level gold sample.")
    parser.add_argument("--gold-path", default="output/bench/chapter_level_gold_standard_v1.json")
    parser.add_argument("--out", default="/tmp/chapter_level_gold_sample.json")
    parser.add_argument("--fraction", type=float, default=0.1, help="Fraction per book (default 0.1 = 10%%)")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    gold = json.loads(Path(args.gold_path).read_text(encoding="utf-8"))
    queries = gold.get("queries", [])
    sample = stratified_sample(queries, args.fraction, args.seed)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({"queries": sample}, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Sampled {len(sample)}/{len(queries)} queries (fraction={args.fraction}, seed={args.seed})")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
