#!/usr/bin/env python3
"""RPV Preflight — read-only retrieval execution for RPV-01~05, 07.

Does NOT modify any code, corpus, or index. Only reads and reports.
"""

import json
import sys
import time
from pathlib import Path

# Activate venv if not already
import os
venv = Path.home() / "envs" / "dbma311"
if not (Path(sys.executable).resolve().parent.parent == venv.resolve()):
    # Try to activate
    pass  # User should have activated; we'll import directly

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.retrieval import RetrievalEngine, QueryProcessor, RankedCandidate, ParsedQuery
from core.config import DEFAULT_TSU_DATASET_PATH

# ============================================================
# RPV Questions (from GS-FINAL-RPV-TEST-SET-DRAFT.md)
# ============================================================
RPV_QUESTIONS = {
    "RPV-01a": "로마서 8장 28절의 헬라어 원문에서 \"모든 것이 합력하여 선을 이룬다\"는 표현의 문법 구조는 어떻게 되어 있습니까?",
    "RPV-01b": "요한일서와 요한복음에서 \"사랑\"(ἀγάπη)이 사용되는 용례 차이가 있습니까?",
    "RPV-02": "야고보서 2장의 \"행함이 없는 믿음은 죽은 것\"이라는 구절을 로마서의 이신칭의 교리와 어떻게 조화시킬 수 있습니까?",
    "RPV-03a": "개혁주의 관점에서 예정론과 인간의 자유의지는 어떻게 양립합니까?",
    "RPV-03b": "침례교 신앙고백(1689 LBC 등)에서 성찬에 대한 입장은 무엇입니까?",
    "RPV-04": "1세기 로마 제국의 노예 제도가 빌레몬서의 배경을 이해하는 데 어떤 영향을 줍니까?",
    "RPV-05a": "산상수훈의 팔복(마태복음 5장)에 대해 여러 주석가들의 해석을 비교해 주십시오.",
    "RPV-05b": "칭의(justification) 교리에 대해 Fuller와 다른 저자들의 견해 차이가 있습니까?",
    "RPV-07": "이번 주 설교 본문이 누가복음 15장(잃어버린 아들 비유)입니다. 설교 개요를 짜는 데 참고할 신학적/역사적 포인트를 정리해 주십시오.",
}

# ============================================================
# Main
# ============================================================
def main():
    print("=" * 70)
    print("RPV PREFLIGHT — Retrieval Execution (read-only)")
    print(f"TSU Dataset: {DEFAULT_TSU_DATASET_PATH}")
    print(f"TSU Count: 204,262")
    print("=" * 70)

    # Initialize engine and processor
    engine = RetrievalEngine(tsu_dataset_path=DEFAULT_TSU_DATASET_PATH)
    processor = QueryProcessor(engine=engine)

    results = {}

    for rpv_id, query_text in RPV_QUESTIONS.items():
        print(f"\n{'='*70}")
        print(f"RPV-ID: {rpv_id}")
        print(f"Query:  {query_text}")
        print("-" * 70)

        t0 = time.perf_counter()
        response = processor.process(query=query_text, query_id=rpv_id, k=10)
        elapsed_ms = (time.perf_counter() - t0) * 1000

        candidates = response.candidates if hasattr(response, 'candidates') else []
        # Also check via response dict
        if not candidates and hasattr(response, '__dict__'):
            for attr in ['candidates', 'ranked_candidates', 'results']:
                if hasattr(response, attr):
                    candidates = getattr(response, attr)
                    break

        # Get raw candidate list
        cand_list = []
        if isinstance(candidates, list):
            cand_list = candidates
        elif isinstance(response, dict):
            cand_list = response.get('candidates', [])
        
        # If still empty, try to access via the ResponsePackage structure
        if not cand_list:
            # ResponsePackage likely has a 'candidates' attribute
            cand_list = getattr(response, 'candidates', [])

        print(f"Execution time: {elapsed_ms:.1f} ms")
        print(f"RankedCandidate count: {len(cand_list)}")

        if cand_list:
            print("Top 3 candidates:")
            for i, c in enumerate(cand_list[:3]):
                if isinstance(c, RankedCandidate):
                    print(f"  [{i+1}] tsu_id={c.tsu_id} final_score={c.final_score:.4f}")
                    print(f"       content={c.content[:200]}")
                    print(f"       metadata={c.metadata}")
                elif isinstance(c, dict):
                    print(f"  [{i+1}] tsu_id={c.get('tsu_id')} final_score={c.get('final_score', 0):.4f}")
                    print(f"       content={c.get('content', '')[:200]}")
                else:
                    print(f"  [{i+1}] {type(c)}: {str(c)[:200]}")
        else:
            print("No candidates returned.")

        results[rpv_id] = {
            "query": query_text,
            "count": len(cand_list),
            "candidates": cand_list,
            "elapsed_ms": elapsed_ms,
        }

    # ============================================================
    # Summary table
    # ============================================================
    print(f"\n{'='*70}")
    print("RPV PREFLIGHT SUMMARY")
    print("=" * 70)
    print(f"{'RPV-ID':<10} {'Count':>6} {'Elapsed(ms)':>12} {'Verdict':<30}")
    print("-" * 70)
    for rpv_id in RPV_QUESTIONS:
        r = results[rpv_id]
        verdict = "grounded 가능" if r["count"] > 0 else "insufficient_evidence가 정상"
        print(f"{rpv_id:<10} {r['count']:>6} {r['elapsed_ms']:>12.1f} {verdict:<30}")

    # Save raw results for later reference
    output_path = Path("output/rpv_preflight_raw.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Serialize results (strip non-serializable objects)
    serializable = {}
    for rpv_id, r in results.items():
        cands = []
        for c in r["candidates"]:
            if isinstance(c, RankedCandidate):
                cands.append(c.to_dict())
            elif isinstance(c, dict):
                cands.append(c)
            else:
                cands.append(str(c))
        serializable[rpv_id] = {
            "query": r["query"],
            "count": r["count"],
            "candidates": cands,
            "elapsed_ms": r["elapsed_ms"],
        }
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(serializable, f, ensure_ascii=False, indent=2)
    print(f"\nRaw results saved to: {output_path}")

if __name__ == "__main__":
    main()
