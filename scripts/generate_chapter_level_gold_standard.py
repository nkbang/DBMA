#!/usr/bin/env python3
"""scripts/generate_chapter_level_gold_standard.py — Chapter-level Gold Standard v1.

SPRINT18-D: extends the book-level Gold generation pipeline
(generate_book_level_gold_standard.py) with a chapter dimension, reusing
its core design (deterministic book x intent x language combinatorics,
schema additivity, current-corpus-only scope) rather than redesigning it.

Two filters stand between SPRINT18-C's raw verse_mapping.chapter data and
a trustworthy Gold query (Phase18-D Preflight findings):

  1. Canonical chapter range validation — SPRINT18-C's _resolve_chapter()
     takes the first ScriptureReference match in a chunk's content, with
     no plausibility check. On this corpus's English commentaries, index/
     appendix pages (e.g. "APPENDIX II: THE CHRONOLOGY...") contain
     colon-adjacent digit sequences that happen to match the reference
     regex but are page numbers or dates, not real chapters — e.g. 2
     Kings chapter values as high as 748 were observed, though 2 Kings
     canonically has 25 chapters. 86 of 243 distinct (book, chapter)
     pairs found in the raw TSU data (35.4%) fall outside the book's
     real chapter count.
  2. Density threshold (records >= 3) — a (book, chapter) pair backed by
     only 1-2 TSU records risks the Gold query's ground truth resting on
     a single noisy/OCR-damaged chunk (noise chunks are ~11.1% of this
     corpus per the Phase6A-3 Dataset Quality Audit).

Evaluation policy (recorded in this dataset's metadata for SPRINT18-E to
consume, not implemented here — this script only generates the Gold set):
  Benchmark judging must use exact book_id AND exact chapter match.
  RetrievalEngine._metadata_filter()'s +/-2 chapter tolerance is a
  retrieval-time recall aid, not a correctness definition, and must not
  be reused as the Benchmark's pass/fail criterion.

Usage:
    python -m scripts.generate_chapter_level_gold_standard --dry-run
    python -m scripts.generate_chapter_level_gold_standard
"""

from __future__ import annotations

import argparse
import datetime
import json
from collections import Counter
from pathlib import Path
from typing import Any

from core.config import DEFAULT_BENCH_DIR, DEFAULT_TSU_DATASET_PATH
from core.canonical_constants import CANONICAL_MAX_CHAPTER
from scripts.generate_book_level_gold_standard import CORPUS_BOOKS

MIN_DENSITY = 3  # minimum TSU records backing a (book, chapter) pair

# (intent_name, language, question_template). {kr}/{en} = book name,
# {chapter} = chapter number. Adapted from
# generate_book_level_gold_standard.py's 6 book-level intents — same
# combinatorial-diversity principle (SPRINT17 lesson: v3's gold standard
# collapsed to a single repeated theme; explicit intent x language
# combinatorics is what prevents that here too).
_INTENT_TEMPLATES: list[tuple[str, str, str]] = [
    ("simple_lookup", "ko", "{kr} {chapter}장 자료를 찾아라"),
    ("simple_lookup", "en", "Find resources about {en} chapter {chapter}"),
    ("content_exploration", "ko", "{kr} {chapter}장의 주요 내용은 무엇인가?"),
    ("content_exploration", "en", "What are the main contents of {en} chapter {chapter}?"),
    ("theological_topic", "ko", "{kr} {chapter}장에서 다루는 신학적 주제는 무엇인가?"),
    ("theological_topic", "en", "What theological themes does {en} chapter {chapter} address?"),
    ("sermon_preparation", "ko", "{kr} {chapter}장 본문으로 설교를 준비하려면 어떤 자료가 필요한가?"),
    ("sermon_preparation", "en", "What resources are needed to prepare a sermon from {en} chapter {chapter}?"),
    ("historical_context", "ko", "{kr} {chapter}장의 역사적 배경은 무엇인가?"),
    ("historical_context", "en", "What is the historical background of {en} chapter {chapter}?"),
    ("internal_comparison", "ko", "{kr} {chapter}장 안에서 서로 다른 두 구절을 비교해줘"),
    ("internal_comparison", "en", "Compare two different passages within {en} chapter {chapter}"),
]


def load_chapter_density(tsu_path: str | Path) -> Counter:
    """Count TSU records per (book_id, chapter) from the live TSU dataset —
    read-only, no assumptions baked in beyond what's actually in the file."""
    counts: Counter = Counter()
    with open(tsu_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            vm = rec.get("verse_mapping", {})
            book_id = vm.get("book_id")
            chapter = vm.get("chapter")
            if book_id and chapter is not None:
                counts[(book_id, chapter)] += 1
    return counts


def select_chapters(density: Counter) -> dict[str, Any]:
    """Apply canonical range validation then density threshold. Returns a
    report dict with every intermediate count PM asked for, plus the
    final selected (book, chapter) list."""
    candidate_pairs = [(b, c) for (b, c) in density if b in CORPUS_BOOKS]

    canonical_valid = [
        (b, c) for (b, c) in candidate_pairs
        if 1 <= c <= CANONICAL_MAX_CHAPTER.get(b, 0)
    ]
    canonical_rejected = len(candidate_pairs) - len(canonical_valid)

    density_valid = [(b, c) for (b, c) in canonical_valid if density[(b, c)] >= MIN_DENSITY]
    density_rejected = len(canonical_valid) - len(density_valid)

    return {
        "candidate_pairs_count": len(candidate_pairs),
        "canonical_valid_count": len(canonical_valid),
        "canonical_rejected_count": canonical_rejected,
        "density_valid_count": len(density_valid),
        "density_rejected_count": density_rejected,
        "selected_pairs": sorted(density_valid),
    }


def generate_queries(selected_pairs: list[tuple[str, int]]) -> list[dict[str, Any]]:
    """Deterministic — same selected_pairs always produces the same
    query list (only "id" sequence numbers depend on CORPUS_BOOKS/pair
    iteration order, which is itself deterministic)."""
    queries: list[dict[str, Any]] = []
    seq = 0
    # Group by book so IDs read as CHAPTER-{book}-{seq}, mirroring
    # generate_book_level_gold_standard.py's BOOK-{book}-{seq} convention.
    for book_id in CORPUS_BOOKS:
        kr, en = CORPUS_BOOKS[book_id]
        chapters = sorted(c for (b, c) in selected_pairs if b == book_id)
        for chapter in chapters:
            for intent, lang, template in _INTENT_TEMPLATES:
                seq += 1
                question = template.format(kr=kr, en=en, chapter=chapter)
                queries.append({
                    "id": f"CHAPTER-{book_id}-{seq:04d}",
                    "question": question,
                    "expected_book_id": book_id,
                    "expected_chapter": chapter,
                    "language": lang,
                    "intent": intent,
                    "generated_from": "chapter_id_template",
                })
    return queries


def validate(queries: list[dict[str, Any]]) -> dict[str, Any]:
    """Read-only validation — mirrors generate_book_level_gold_standard.py's
    validate() shape."""
    valid_book_ids = set(CORPUS_BOOKS.keys())
    issues: list[str] = []

    questions_seen: dict[str, str] = {}
    for q in queries:
        if q["expected_book_id"] not in valid_book_ids:
            issues.append(f"{q['id']}: invalid expected_book_id {q['expected_book_id']!r}")
        max_ch = CANONICAL_MAX_CHAPTER.get(q["expected_book_id"], 0)
        if not (1 <= q["expected_chapter"] <= max_ch):
            issues.append(f"{q['id']}: expected_chapter {q['expected_chapter']} out of canonical range (1-{max_ch})")
        if q["question"] in questions_seen:
            issues.append(f"{q['id']}: duplicate question (also in {questions_seen[q['question']]})")
        else:
            questions_seen[q["question"]] = q["id"]

    book_distribution: dict[str, int] = {}
    chapter_distribution: dict[str, int] = {}
    for q in queries:
        book_distribution[q["expected_book_id"]] = book_distribution.get(q["expected_book_id"], 0) + 1
        key = f"{q['expected_book_id']}-{q['expected_chapter']}"
        chapter_distribution[key] = chapter_distribution.get(key, 0) + 1

    return {
        "total_queries": len(queries),
        "unique_questions": len(questions_seen),
        "book_distribution": book_distribution,
        "chapter_distribution": chapter_distribution,
        "chapters_covered_count": len(chapter_distribution),
        "issues": issues,
        "passed": len(issues) == 0,
    }


def build_dataset(queries: list[dict[str, Any]], selection_report: dict[str, Any]) -> dict[str, Any]:
    now = datetime.datetime.now().isoformat(timespec="seconds")
    return {
        "metadata": {
            "dataset_version": "chapter-level-v1",
            "generated_at": now,
            "source_dataset": "extends output/bench/book_level_gold_standard_v1.json "
                               "with a chapter dimension",
            "documents_covered": 12,
            "books_covered": sorted(CORPUS_BOOKS.keys()),
            "query_count": len(queries),
            "generation_policy": "expected_book_id + expected_chapter (no expected_tsu_ids); "
                                  "6 intents x {ko,en} per selected (book,chapter) pair; "
                                  "canonical chapter range + density>=3 filtering applied",
            "canonical_max_chapter": CANONICAL_MAX_CHAPTER,
            "min_density": MIN_DENSITY,
            "chapter_selection": {
                "candidate_pairs_count": selection_report["candidate_pairs_count"],
                "canonical_valid_count": selection_report["canonical_valid_count"],
                "canonical_rejected_count": selection_report["canonical_rejected_count"],
                "density_valid_count": selection_report["density_valid_count"],
                "density_rejected_count": selection_report["density_rejected_count"],
            },
            "evaluation_policy": "exact book_id AND exact chapter match — "
                                  "RetrievalEngine._metadata_filter()'s +/-2 chapter "
                                  "tolerance is a retrieval-time recall aid, not the "
                                  "Benchmark's correctness definition, and must not be "
                                  "reused for pass/fail judging (SPRINT18-E).",
        },
        "queries": queries,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the chapter-level Gold Standard v1.")
    parser.add_argument("--tsu-path", default=DEFAULT_TSU_DATASET_PATH)
    parser.add_argument("--output-path", default=str(Path(DEFAULT_BENCH_DIR) / "chapter_level_gold_standard_v1.json"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    density = load_chapter_density(args.tsu_path)
    selection_report = select_chapters(density)
    queries = generate_queries(selection_report["selected_pairs"])
    report = validate(queries)

    print("=== Chapter Selection Report ===")
    print(json.dumps({k: v for k, v in selection_report.items() if k != "selected_pairs"}, ensure_ascii=False, indent=2))
    print()
    print("=== Validation Report ===")
    print(json.dumps({k: v for k, v in report.items() if k not in ("chapter_distribution",)}, ensure_ascii=False, indent=2))
    print()
    print("=== Chapter Distribution ===")
    print(json.dumps(report["chapter_distribution"], ensure_ascii=False, indent=2))

    if not report["passed"]:
        print("VALIDATION FAILED — not writing output.")
        raise SystemExit(1)

    if args.dry_run:
        print(f"[DRY-RUN] would write {len(queries)} queries to {args.output_path}")
        return

    dataset = build_dataset(queries, selection_report)
    out_path = Path(args.output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(queries)} queries to {out_path}")


if __name__ == "__main__":
    main()
