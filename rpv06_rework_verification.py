#!/usr/bin/env python3
"""RPV-06a/06b REWORK verification - live retrieval test with QueryParser."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "core"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.retrieval import RetrievalEngine, QueryParser
from core.query_planner import classify

FIXTURE_A_PATTERNS = ("TSU-JHN-6f323b08ce388551d2fa772c756a828e_chunk_",)
FIXTURE_B_PATTERNS = ("TSU-UNK-5ce2824e947da15da8893fbb45c07239_chunk_",)

CANDIDATES = {
    "RPV-06a-c1": "포도나무와 가지의 비유에서 열매를 맺기 위해 주님 안에 거한다는 의미를 설명해 주세요",
    "RPV-06a-c2": "예수님이 요한복음 15장에서 포도나무 비유로 가르친 거함의 의미가 무엇입니까",
    "RPV-06a-c3": "참 포도나무요 아버지는 농부라 - 요한복음 15장 묵상 노트",
    "RPV-06a-c4": "거하라 mene - 요한복음 15장의 지속적 관계 개념에 대해 설명해 주세요",
    "RPV-06a-c5": "가지치기 καθαίρω - 더 많은 열매를 위한 손질, 요한복음 15장 2절",
    "RPV-06a-c6": "요한복음 15:1-8 포도나무 비유 — 거하라 mene 의미",
    "RPV-06a-c7": "요 15:1 참 포도나무요 아버지는 농부라",
    "RPV-06b-c1": "성령께서 교회에 다양한 은사를 주신다는 관점에서 은사의 종류와 목적을 정리해 주세요",
    "RPV-06b-c2": "고린도전서 12장에서 성령의 은사 목록과 그 목적을 설명해 주세요",
    "RPV-06b-c3": "은사의 종류와 목적 - 고전 12장 개인 연구 메모",
    "RPV-06b-c4": "각 사람에게 유익하게 하려 하심이라 - 성령 은사의 공동체적 목적",
    "RPV-06b-c5": "고전 12:8-10 성령의 은사 목록",
    "RPV-06b-c6": "고린도전서 12:7 각 사람에게 유익하게 하려 하심이라",
}

def check_fixture_hit(candidates, patterns):
    hits = []
    for i, c in enumerate(candidates):
        tsu_id = getattr(c, "tsu_id", "") or ""
        src_file = getattr(c, "source_file", "") or str(getattr(c, "metadata", {}).get("source_file", ""))
        for pat in patterns:
            if pat in tsu_id or pat in src_file:
                hits.append({
                    "rank": i,
                    "tsu_id": tsu_id,
                    "source_file": src_file,
                    "bm25": getattr(c, "bm25_score", None),
                    "theological": getattr(c, "theological_score", None),
                    "final": getattr(c, "final_score", None),
                })
                break
    return hits

def main():
    pwd = Path.cwd()
    print(f"PWD: {pwd}")
    assert str(pwd) == "/Users/David/DBMA-rpv-c8f7e41a", f"WRONG DIR: {pwd}"

    tsu_path = Path("output/bench/tsu_dataset.jsonl")
    engine = RetrievalEngine(tsu_dataset_path=tsu_path)
    parser = QueryParser()
    print(f"\n=== ENGINE STATUS ===")
    print(f"TSU corpus docs: {len(engine.tsus)}")

    fixture_a_in_engine = [tid for tid in engine.tsus if "rpv_fixture_A" in str(tid)]
    fixture_b_in_engine = [tid for tid in engine.tsus if "rpv_fixture_B" in str(tid)]
    print(f"Fixture A chunks in engine: {len(fixture_a_in_engine)}")
    print(f"Fixture B chunks in engine: {len(fixture_b_in_engine)}")

    results = {}
    for label, query in CANDIDATES.items():
        parsed = parser.parse(query)
        plan = classify(query, parsed)
        candidates, metrics = engine.retrieve(parsed_query=parsed, k_output=10, file_scope=None)
        fixture_a_hits = check_fixture_hit(candidates, FIXTURE_A_PATTERNS)
        fixture_b_hits = check_fixture_hit(candidates, FIXTURE_B_PATTERNS)

        top_sources = []
        top_scores = []
        for c in candidates[:10]:
            src = getattr(c, "source_file", "") or str(getattr(c, "metadata", {}).get("source_file", ""))
            top_sources.append(Path(src).name if src else "?")
            top_scores.append(getattr(c, "final_score", None))

        result = {
            "query": query,
            "route": plan.route,
            "reason": plan.reason,
            "scripture_refs": [str(r) for r in parsed.scripture_refs],
            "detected_books": parsed.detected_books,
            "themes": parsed.themes,
            "keywords": parsed.keywords[:10],
            "candidate_count": len(candidates),
            "top_10_sources": top_sources,
            "top_10_scores": top_scores,
            "fixture_a_hits": fixture_a_hits,
            "fixture_b_hits": fixture_b_hits,
            "fixture_a_count": len(fixture_a_hits),
            "fixture_b_count": len(fixture_b_hits),
        }
        results[label] = result

    print(f"\n{'='*70}")
    print("RPV-06a/06b REWORK VERIFICATION RESULTS")
    print(f"{'='*70}")

    for label in sorted(results.keys()):
        r = results[label]
        is_06a = "06a" in label
        is_06b = "06b" in label
        target_fixture = "A" if is_06a else ("B" if is_06b else "?")

        print(f"\n--- {label} (target: Fixture {target_fixture}) ---")
        print(f"  Query: {r['query']}")
        print(f"  Route: {r['route']} | Reason: {r['reason']}")
        print(f"  Scripture refs: {r['scripture_refs']}")
        print(f"  Detected books: {r['detected_books']}")
        print(f"  Themes: {r['themes']}")
        print(f"  Keywords: {r['keywords']}")
        print(f"  Candidate count: {r['candidate_count']}")
        print(f"  Top-10 sources:")
        for i, (src, score) in enumerate(zip(r['top_10_sources'], r['top_10_scores'])):
            print(f"    [{i}] {src} (score={score})")

        if is_06a:
            print(f"  Fixture A hits in top-10: {r['fixture_a_count']}")
            for h in r['fixture_a_hits']:
                print(f"    rank[{h['rank']}] tsu_id={h['tsu_id'][:50]}... bm25={h['bm25']} final={h['final']}")
        if is_06b:
            print(f"  Fixture B hits in top-10: {r['fixture_b_count']}")
            for h in r['fixture_b_hits']:
                print(f"    rank[{h['rank']}] tsu_id={h['tsu_id'][:50]}... bm25={h['bm25']} final={h['final']}")

    print(f"\n{'='*70}")
    print("SUMMARY TABLE")
    print(f"{'='*70}")
    print(f"{'Label':<20} {'Route':<12} {'Fixture':<8} {'Hits':<6} {'Top-1 Source':<40} {'ScriptureRefs'}")
    print("-" * 110)
    for label in sorted(results.keys()):
        r = results[label]
        target = "A" if "06a" in label else ("B" if "06b" in label else "?")
        hits = r[f"fixture_{target.lower()}_count"]
        top_src = r['top_10_sources'][0] if r['top_10_sources'] else "?"
        sr = ",".join(r['scripture_refs'])[:30] or "(none)"
        print(f"{label:<20} {r['route']:<12} {target:<8} {hits:<6} {top_src:<40} {sr}")

    output_path = Path("output/bench/rpv06_rework_verification.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nJSON output written to: {output_path}")

    return results

if __name__ == "__main__":
    main()
