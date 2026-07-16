#!/usr/bin/env python3
"""scripts/generate_book_level_gold_standard.py — Book-level Gold Standard v1.

SPRINT17-Phase6B-1: replaces the retired dbma_gold_standard_v3.json
(348 queries, single theme "covenant faithfulness" repeated across all of
them, 70.7% targeting books/documents not in the current corpus,
expected_tsu_ids that go stale on every TSU rebuild — see Phase6A-3
Dataset Quality Audit and Phase6B-1 design report).

Design (per Phase6B-1 approval):
  - expected_book_id replaces expected_tsu_ids entirely — this is the
    schema's core change. It survives TSU rebuilds because book_id
    (Phase6A-1/2, 100% coverage) is stable; tsu_id's sequential
    numbering is not.
  - Covers only the 8 book_ids actually present in the current 12-document
    corpus (MRK, JHN, ACT, ROM, 1CO, 2CO, 2KI, 2CH) — no external books.
  - Six distinct query intents per book (simple lookup, content
    exploration, theological topic, sermon prep, historical context,
    internal comparison) in both Korean and English, so the same
    expected_book_id is reached via genuinely different question
    phrasings — this is the fix for the single-theme degenerate pattern
    found in v3, not a cosmetic template swap.

Usage:
    python -m scripts.generate_book_level_gold_standard --dry-run
    python -m scripts.generate_book_level_gold_standard
"""

from __future__ import annotations

import argparse
import datetime
import json
from pathlib import Path
from typing import Any

from core.config import DEFAULT_BENCH_DIR

# book_id -> (Korean name, English name) — sourced from the current
# 12-document corpus only (Phase6A-1 backfill), not the full biblical
# canon in core.retrieval.BOOK_ID_TO_NAMES.
CORPUS_BOOKS: dict[str, tuple[str, str]] = {
    "MRK": ("마가복음", "Mark"),
    "JHN": ("요한복음", "John"),
    "ACT": ("사도행전", "Acts"),
    "ROM": ("로마서", "Romans"),
    "1CO": ("고린도전서", "1 Corinthians"),
    "2CO": ("고린도후서", "2 Corinthians"),
    "2KI": ("열왕기하", "2 Kings"),
    "2CH": ("역대하", "2 Chronicles"),
}

# Each entry: (intent_name, language, question_template).
# question_template takes {kr} or {en} depending on language.
_INTENT_TEMPLATES: list[tuple[str, str, str]] = [
    ("simple_lookup", "ko", "{kr} 자료를 찾아라"),
    ("simple_lookup", "en", "Find resources about {en}"),
    ("content_exploration", "ko", "{kr}의 주요 내용은 무엇인가?"),
    ("content_exploration", "en", "What are the main contents of {en}?"),
    ("theological_topic", "ko", "{kr}에서 다루는 신학적 주제는 무엇인가?"),
    ("theological_topic", "en", "What theological themes does {en} address?"),
    ("sermon_preparation", "ko", "{kr} 본문으로 설교를 준비하려면 어떤 자료가 필요한가?"),
    ("sermon_preparation", "en", "What resources are needed to prepare a sermon from {en}?"),
    ("historical_context", "ko", "{kr}의 역사적 배경은 무엇인가?"),
    ("historical_context", "en", "What is the historical background of {en}?"),
    ("internal_comparison", "ko", "{kr} 안에서 서로 다른 두 구절을 비교해줘"),
    ("internal_comparison", "en", "Compare two different passages within {en}"),
]


def generate_queries() -> list[dict[str, Any]]:
    """Generate the query list — deterministic, no randomness, so re-running
    this script produces byte-identical output for the same CORPUS_BOOKS/
    _INTENT_TEMPLATES (only generated_at in the manifest changes)."""
    queries: list[dict[str, Any]] = []
    seq = 0
    for book_id, (kr, en) in CORPUS_BOOKS.items():
        for intent, lang, template in _INTENT_TEMPLATES:
            seq += 1
            question = template.format(kr=kr, en=en)
            queries.append({
                "id": f"BOOK-{book_id}-{seq:03d}",
                "question": question,
                "expected_book_id": book_id,
                "language": lang,
                "intent": intent,
                "generated_from": "book_id_template",
            })
    return queries


def validate(queries: list[dict[str, Any]]) -> dict[str, Any]:
    """Read-only validation — does not raise, returns a report dict so the
    caller can decide whether to proceed."""
    valid_book_ids = set(CORPUS_BOOKS.keys())
    issues: list[str] = []

    questions_seen: dict[str, str] = {}
    for q in queries:
        if q["expected_book_id"] not in valid_book_ids:
            issues.append(f"{q['id']}: invalid expected_book_id {q['expected_book_id']!r}")
        if q["question"] in questions_seen:
            issues.append(f"{q['id']}: duplicate question (also in {questions_seen[q['question']]})")
        else:
            questions_seen[q["question"]] = q["id"]

    book_distribution: dict[str, int] = {}
    for q in queries:
        book_distribution[q["expected_book_id"]] = book_distribution.get(q["expected_book_id"], 0) + 1

    return {
        "total_queries": len(queries),
        "unique_questions": len(questions_seen),
        "book_distribution": book_distribution,
        "books_covered": sorted(book_distribution.keys()),
        "books_covered_count": len(book_distribution),
        "issues": issues,
        "passed": len(issues) == 0 and set(book_distribution.keys()) == valid_book_ids,
    }


def build_dataset(queries: list[dict[str, Any]]) -> dict[str, Any]:
    now = datetime.datetime.now().isoformat(timespec="seconds")
    return {
        "metadata": {
            "dataset_version": "book-level-v1",
            "generated_at": now,
            "source_dataset": "retires output/SPRINT5_ENGINEERING_VALIDATION/dbma_gold_standard_v3.json "
                               "(single-theme degenerate, 70.7% off-corpus, tsu_id-based)",
            "documents_covered": 12,
            "books_covered": sorted(CORPUS_BOOKS.keys()),
            "query_count": len(queries),
            "generation_policy": "expected_book_id only (no expected_tsu_ids); "
                                  "6 intents x {ko,en} per book, current-corpus books only",
        },
        "queries": queries,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the book-level Gold Standard v1.")
    parser.add_argument("--output-path", default=str(Path(DEFAULT_BENCH_DIR) / "book_level_gold_standard_v1.json"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    queries = generate_queries()
    report = validate(queries)

    print("=== Validation Report ===")
    print(json.dumps(report, ensure_ascii=False, indent=2))

    if not report["passed"]:
        print("VALIDATION FAILED — not writing output.")
        raise SystemExit(1)

    if args.dry_run:
        print(f"[DRY-RUN] would write {len(queries)} queries to {args.output_path}")
        return

    dataset = build_dataset(queries)
    out_path = Path(args.output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(queries)} queries to {out_path}")


if __name__ == "__main__":
    main()
