#!/usr/bin/env python3
"""RPV-06a/06b preflight — run queries with file_scope on fixture documents.

Runs in the isolated c8f7e41a worktree only.
"""

import json
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "core"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.retrieval import RetrievalEngine, ParsedQuery

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("rpv_preflight")


def make_parsed_query(text: str) -> ParsedQuery:
    """Create a minimal ParsedQuery from raw text."""
    return ParsedQuery(
        original_query=text,
        intent="unknown",
        scripture_refs=[],
        detected_books=[],
        themes=[],
        keywords=[],
        language="ko",
        author="",
        source_book="",
        translated_terms=[],
        translated_phrases=[],
    )


def run_query(engine, query_text, file_scope=None, label=""):
    """Run a single query and return results."""
    logger.info("=" * 60)
    logger.info("Query: %s", query_text)
    if file_scope:
        logger.info("file_scope: %s", file_scope)
    else:
        logger.info("file_scope: (none)")

    try:
        parsed = make_parsed_query(query_text)
        candidates, metrics = engine.retrieve(
            parsed_query=parsed,
            k_output=10,
            file_scope=file_scope,
        )
        logger.info("Retrieved %d candidates", len(candidates))
        for i, r in enumerate(candidates[:5]):
            sf = r.metadata.get("source_file", "N/A")
            logger.info("  [%d] score=%.4f source=%s tsu_id=%s",
                        i, r.final_score, sf, r.tsu_id)
            content_preview = (r.content or "")[:80].replace("\n", " ")
            logger.info("      content: %s...", content_preview)
        return candidates
    except Exception as e:
        logger.error("Query FAILED: %s — %s", type(e).__name__, e)
        import traceback
        traceback.print_exc()
        return None


def main():
    tsu_path = Path("output/bench/tsu_dataset.jsonl")
    if not tsu_path.exists():
        logger.error("TSU dataset not found: %s", tsu_path)
        sys.exit(1)

    logger.info("Initializing RetrievalEngine (tsu=%s)...", tsu_path)
    engine = RetrievalEngine(tsu_dataset_path=tsu_path)
    logger.info("RetrievalEngine initialized. TSU corpus loaded: %d docs", len(engine.tsus))

    # RPV-06a query
    rpv_06a_query = "요한복음 15장 포도나무 비유 설교노트 관련해 참고할 만한 추가 자료가 있습니까?"
    rpv_06a_scope = ["rpv_fixture_A_john15_sermon_notes.txt"]

    # RPV-06b query
    rpv_06b_query = "성령의 은사 제 개인 서재 자료를 우선으로, 부족하면 기본 코퍼스에서 보충해서 정리해 주십시오."
    rpv_06b_scope = ["rpv_fixture_B_spirit_gifts_notes.txt"]

    # ── Test 1: RPV-06a with file_scope ─────────────────────────
    logger.info("\n### RPV-06a with file_scope ###")
    results_06a = run_query(engine, rpv_06a_query, file_scope=rpv_06a_scope, label="RPV-06a")

    # ── Test 2: RPV-06b with file_scope ─────────────────────────
    logger.info("\n### RPV-06b with file_scope ###")
    results_06b = run_query(engine, rpv_06b_query, file_scope=rpv_06b_scope, label="RPV-06b")

    # ── Test 3: RPV-06a without file_scope (baseline) ───────────
    logger.info("\n### RPV-06a WITHOUT file_scope (baseline) ###")
    results_06a_no_scope = run_query(engine, rpv_06a_query, label="RPV-06a baseline")

    # ── Test 4: RPV-06b without file_scope (baseline) ───────────
    logger.info("\n### RPV-06b WITHOUT file_scope (baseline) ###")
    results_06b_no_scope = run_query(engine, rpv_06b_query, label="RPV-06b baseline")

    # ── Summary ──────────────────────────────────────────────────
    logger.info("=" * 60)
    summary = {
        "rpv_06a_with_scope": len(results_06a) if results_06a else 0,
        "rpv_06b_with_scope": len(results_06b) if results_06b else 0,
        "rpv_06a_no_scope": len(results_06a_no_scope) if results_06a_no_scope else 0,
        "rpv_06b_no_scope": len(results_06b_no_scope) if results_06b_no_scope else 0,
    }
    for k, v in summary.items():
        logger.info("  %s: %d results", k, v)

    if results_06a:
        fixture_in_results = any(r.metadata.get("source_file") == "rpv_fixture_A_john15_sermon_notes.txt" for r in results_06a)
        logger.info("  RPV-06a: fixture document in results: %s", fixture_in_results)

    if results_06b:
        fixture_in_results = any(r.metadata.get("source_file") == "rpv_fixture_B_spirit_gifts_notes.txt" for r in results_06b)
        logger.info("  RPV-06b: fixture document in results: %s", fixture_in_results)

    # Write results to JSON
    result_path = Path("output/bench/rpv_preflight_result.json")
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_data = {
        "rpv_06a_with_scope": {
            "query": rpv_06a_query,
            "file_scope": rpv_06a_scope,
            "result_count": len(results_06a) if results_06a else 0,
            "results": [
                {"source_file": r.metadata.get("source_file"), "final_score": r.final_score, "tsu_id": r.tsu_id}
                for r in (results_06a or [])[:5]
            ],
        },
        "rpv_06b_with_scope": {
            "query": rpv_06b_query,
            "file_scope": rpv_06b_scope,
            "result_count": len(results_06b) if results_06b else 0,
            "results": [
                {"source_file": r.metadata.get("source_file"), "final_score": r.final_score, "tsu_id": r.tsu_id}
                for r in (results_06b or [])[:5]
            ],
        },
        "rpv_06a_no_scope": {
            "query": rpv_06a_query,
            "result_count": len(results_06a_no_scope) if results_06a_no_scope else 0,
            "results": [
                {"source_file": r.metadata.get("source_file"), "final_score": r.final_score, "tsu_id": r.tsu_id}
                for r in (results_06a_no_scope or [])[:5]
            ],
        },
        "rpv_06b_no_scope": {
            "query": rpv_06b_query,
            "result_count": len(results_06b_no_scope) if results_06b_no_scope else 0,
            "results": [
                {"source_file": r.metadata.get("source_file"), "final_score": r.final_score, "tsu_id": r.tsu_id}
                for r in (results_06b_no_scope or [])[:5]
            ],
        },
    }
    result_path.write_text(json.dumps(result_data, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Results written to: %s", result_path)


if __name__ == "__main__":
    main()
