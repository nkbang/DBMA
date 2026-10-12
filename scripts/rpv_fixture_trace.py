#!/usr/bin/env python3
"""RPV-06 fixture candidate generation pipeline tracer.

Reads-only: does NOT modify code/index/corpus.
Traces 6 stages to find where fixture TSUs disappear.

Run from /Users/David/DBMA-rpv-c8f7e41a directory.
"""

import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "core"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.retrieval import RetrievalEngine, ParsedQuery

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("rpv_trace")


def write_stage(stage_name, data, output_path):
    with open(output_path, "a", encoding="utf-8") as f:
        sep = chr(61) * 60
        f.write(f"\n{sep}\nSTAGE: {stage_name}\n{sep}\n")
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main():
    pwd = Path.cwd()
    logger.info("PWD: %s", pwd)
    assert str(pwd) == "/Users/David/DBMA-rpv-c8f7e41a", f"WRONG DIR: {pwd}"

    output_path = Path("output/bench/rpv_fixture_trace.json")
    if output_path.exists():
        output_path.unlink()

    tsu_path = Path("output/bench/tsu_dataset.jsonl")
    logger.info("TSU dataset: %s", tsu_path)

    # STEP 1: Engine init + index verification
    logger.info("\n### STEP 1: Engine init + index verification ###")
    engine = RetrievalEngine(tsu_dataset_path=tsu_path)
    logger.info("TSU corpus loaded: %d docs", len(engine.tsus))

    fixture_a_in_engine = [tid for tid in engine.tsus if "rpv_fixture_A" in str(tid)]
    fixture_b_in_engine = [tid for tid in engine.tsus if "rpv_fixture_B" in str(tid)]

    step1 = {
        "engine_tsu_count": len(engine.tsus),
        "fixture_a_in_engine": len(fixture_a_in_engine),
        "fixture_b_in_engine": len(fixture_b_in_engine),
    }
    write_stage("STEP_1_engine_index", step1, output_path)
    logger.info("Fixture A in engine: %d, Fixture B in engine: %d",
                len(fixture_a_in_engine), len(fixture_b_in_engine))

    # STEP 2: Exact/free-text search for fixture content (no-scope)
    logger.info("\n### STEP 2: Exact phrase search (no-scope) ###")
    fixture_a_phrases = ["포도나무 비유 설교노트", "거하라", "참 포도나무요"]
    fixture_b_phrases = ["성령의 은사 개인 연구 메모", "각 사람에게 유익하게 하려 하심이라"]

    step2_results = {}
    for label, phrases in [("A", fixture_a_phrases), ("B", fixture_b_phrases)]:
        for phrase in phrases:
            parsed = ParsedQuery(
                original_query=phrase, intent="unknown", scripture_refs=[],
                detected_books=[], themes=[], keywords=[], language="ko",
                author="", source_book="", translated_terms=[], translated_phrases=[],
            )
            candidates, metrics = engine.retrieve(parsed_query=parsed, k_output=10, file_scope=None)
            fixture_hits = [c for c in candidates if f"rpv_fixture_{label}" in str(c.metadata.get("source_file", ""))]
            step2_results[f"phrase_{label}_{phrase[:8]}"] = {
                "query": phrase,
                "total_candidates": len(candidates),
                "fixture_hits": len(fixture_hits),
                "top_3_scores": [c.final_score for c in candidates[:3]],
                "top_3_sources": [c.metadata.get("source_file") for c in candidates[:3]],
            }

    write_stage("STEP_2_exact_phrase_search", step2_results, output_path)
    logger.info("Exact phrase search complete. Results written.")

    # STEP 3: Candidate generation with large candidate_k
    logger.info("\n### STEP 3: Candidate generation with candidate_k=500 ###")
    
    rpv_query = "요한복음 15장 포도나무 비유 설교노트 관련해 참고할 만한 추가 자료가 있습니까?"
    parsed = ParsedQuery(
        original_query=rpv_query, intent="unknown", scripture_refs=[],
        detected_books=[], themes=[], keywords=[], language="ko",
        author="", source_book="", translated_terms=[], translated_phrases=[],
    )

    candidate_k = 500
    candidates, metrics = engine.retrieve(parsed_query=parsed, k_output=candidate_k, file_scope=None)
    fixture_a_in_candidates = [c for c in candidates if "rpv_fixture_A" in str(c.metadata.get("source_file", ""))]
    step3_results = {
        "candidate_k": candidate_k,
        "total_candidates_after_search": len(candidates),
        "fixture_a_in_candidates": {
            "count": len(fixture_a_in_candidates),
            "tsu_ids": [c.tsu_id for c in fixture_a_in_candidates],
            "scores": [c.final_score for c in fixture_a_in_candidates],
            "ranks": [i for i, c in enumerate(candidates) if "rpv_fixture_A" in str(c.metadata.get("source_file", ""))],
        },
    }
    write_stage("STEP_3_candidate_generation_k500", step3_results, output_path)
    logger.info("After search: %d candidates, Fixture A hits: %d",
                len(candidates), len(fixture_a_in_candidates))

    # STEP 4: _demote_index_pages trace (simulated via engine.retrieve with different k)
    logger.info("\n### STEP 4: candidate_k comparison (30 vs 500) ###")
    candidates_k30, _ = engine.retrieve(parsed_query=parsed, k_output=30, file_scope=None)
    candidates_k500, _ = engine.retrieve(parsed_query=parsed, k_output=500, file_scope=None)
    fa_k30 = [c for c in candidates_k30 if "rpv_fixture_A" in str(c.metadata.get("source_file", ""))]
    fa_k500 = [c for c in candidates_k500 if "rpv_fixture_A" in str(c.metadata.get("source_file", ""))]
    step4_results = {
        "candidate_k_30_count": len(candidates_k30),
        "candidate_k_500_count": len(candidates_k500),
        "fixture_a_in_k30": {"count": len(fa_k30),
            "tsu_ids": [c.tsu_id for c in fa_k30],
            "scores": [c.final_score for c in fa_k30]},
        "fixture_a_in_k500": {"count": len(fa_k500),
            "tsu_ids": [c.tsu_id for c in fa_k500],
            "scores": [c.final_score for c in fa_k500]},
    }
    write_stage("STEP_4_candidate_k_comparison", step4_results, output_path)
    logger.info("k=30: %d candidates, Fixture A hits: %d | k=500: %d candidates, Fixture A hits: %d",
                len(candidates_k30), len(fa_k30), len(candidates_k500), len(fa_k500))

    # STEP 5: Full pipeline with k_output=10 (normal condition)
    logger.info("\n### STEP 5: Full pipeline (k=10) ###")
    final_candidates, _ = engine.retrieve(parsed_query=parsed, k_output=10, file_scope=None)
    fa_final = [c for c in final_candidates if "rpv_fixture_A" in str(c.metadata.get("source_file", ""))]
    step5_results = {
        "final_k": 10,
        "total_final_candidates": len(final_candidates),
        "top_10_scores": [c.final_score for c in final_candidates[:10]],
        "top_10_sources": [c.metadata.get("source_file") for c in final_candidates[:10]],
        "fixture_a_in_final": {"count": len(fa_final),
            "tsu_ids": [c.tsu_id for c in fa_final],
            "scores": [c.final_score for c in fa_final]},
    }
    write_stage("STEP_5_final_scoring", step5_results, output_path)
    logger.info("Final top-10: %d candidates, Fixture A hits: %d",
                len(final_candidates), len(fa_final))

    # STEP 6: Compare with file_scope (control)
    logger.info("\n### STEP 6: With file_scope (control) ###")
    scoped_candidates, _ = engine.retrieve(parsed_query=parsed, k_output=10, file_scope=["rpv_fixture_A_john15_sermon_notes.txt"])
    fa_scoped = [c for c in scoped_candidates if "rpv_fixture_A" in str(c.metadata.get("source_file", ""))]
    step6_results = {
        "file_scope": ["rpv_fixture_A_john15_sermon_notes.txt"],
        "total_scoped_candidates": len(scoped_candidates),
        "top_10_scores": [c.final_score for c in scoped_candidates[:10]],
        "top_10_sources": [c.metadata.get("source_file") for c in scoped_candidates[:10]],
        "fixture_a_in_scoped": {"count": len(fa_scoped),
            "tsu_ids": [c.tsu_id for c in fa_scoped],
            "scores": [c.final_score for c in fa_scoped]},
    }
    write_stage("STEP_6_with_file_scope_control", step6_results, output_path)

    logger.info("\n" + "="*60)
    logger.info("ALL STAGES COMPLETE. Results: %s", output_path)
    logger.info("="*60)


if __name__ == "__main__":
    main()
