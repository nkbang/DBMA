#!/usr/bin/env python3
"""scripts/bench_high_throughput.py - high-throughput integration baseline measurement.

Read-only benchmark. Imports existing code but does not modify it.
Output: docs/perf/HIGH_THROUGHPUT_BASELINE_v1.md
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from NAE.pipeline.embed import client as embed_client
from NAE.pipeline.embed import config as embed_config
from NAE.pipeline.tsu import claim as claim_mod
from NAE.pipeline.tsu import config as tsu_config


def _tmp_cache_root() -> Path:
    import tempfile
    return Path(tempfile.mkdtemp(prefix="bench_cache_"))


def _ollama_server_info() -> dict:
    try:
        import subprocess
        result = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=5)
        for line in result.stdout.splitlines():
            if "llama-server" in line and "-np" in line:
                parts = line.split()
                for i, p in enumerate(parts):
                    if p == "-np" and i + 1 < len(parts):
                        return {"parallel": int(parts[i + 1]), "raw": line.strip()}
        try:
            val = os.popen("launchctl getenv OLLAMA_NUM_PARALLEL 2>/dev/null").read().strip()
            if val:
                return {"parallel": int(val), "raw": f"launchctl={val}"}
        except Exception:
            pass
    except Exception:
        pass
    return {"parallel": 1, "raw": "미확인 (기본값 가정)"}


def _system_info() -> dict:
    mem = int(os.popen("sysctl hw.memsize 2>/dev/null").read().split()[-1])
    cpus = int(os.popen("sysctl hw.ncpu 2>/dev/null").read().split()[-1])
    return {"ram_gb": round(mem / 1024**3, 1), "cpus": cpus}


def bench_embedding_single(texts, cache_root, model):
    results, times = [], []
    for i, text in enumerate(texts):
        h = f"bench_single_{i}"
        t0 = time.monotonic()
        vec = embed_client.embed_text(text, content_hash=h, model=model, cache_root=cache_root)
        times.append(time.monotonic() - t0)
        results.append(vec)
    return {
        "method": "single", "count": len(texts),
        "total_sec": round(sum(times), 3),
        "avg_sec": round(sum(times) / len(times), 4) if times else 0,
        "texts_per_sec": round(len(texts) / sum(times), 2) if times else 0,
        "errors": sum(1 for r in results if r is None),
    }


def bench_embedding_batch(texts, cache_root, model):
    items = [(t, f"bench_batch_{i}") for i, t in enumerate(texts)]
    t0 = time.monotonic()
    results = embed_client.embed_texts_batch(items, model=model, cache_root=cache_root)
    elapsed = time.monotonic() - t0
    return {
        "method": "batch", "count": len(texts),
        "total_sec": round(elapsed, 3),
        "texts_per_sec": round(len(texts) / elapsed, 2) if elapsed else 0,
        "errors": sum(1 for r in results if r is None),
    }


def bench_claim_single(candidates, model):
    times, claims, errors = [], 0, 0
    for i, cand in enumerate(candidates):
        t0 = time.monotonic()
        result = claim_mod.extract_claim(
            sentence=cand["text"],
            context_before=cand.get("context_before", ""),
            context_after=cand.get("context_after", ""),
            candidate_scriptures=cand.get("candidate_scriptures", []),
            candidate_citations=cand.get("candidate_citations", []),
            model=model,
        )
        times.append(time.monotonic() - t0)
        if result.is_claim: claims += 1
        if result.error: errors += 1
    return {
        "method": "single", "count": len(candidates),
        "total_sec": round(sum(times), 3),
        "avg_sec": round(sum(times) / len(times), 4) if times else 0,
        "claims_per_sec": round(claims / sum(times), 3) if times else 0,
        "claims_extracted": claims, "errors": errors,
    }


def bench_claim_concurrent(candidates, model, max_workers):
    import concurrent.futures
    def _extract(i, cand):
        return (i, claim_mod.extract_claim(
            sentence=cand["text"],
            context_before=cand.get("context_before", ""),
            context_after=cand.get("context_after", ""),
            candidate_scriptures=cand.get("candidate_scriptures", []),
            candidate_citations=cand.get("candidate_citations", []),
            model=model,
        ))
    t0 = time.monotonic()
    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(_extract, i, c) for i, c in enumerate(candidates)]
        for f in concurrent.futures.as_completed(futures):
            idx, result = f.result()
            results[idx] = result
    elapsed = time.monotonic() - t0
    ordered = [results[i] for i in range(len(candidates))]
    claims = sum(1 for r in ordered if r.is_claim)
    errors = sum(1 for r in ordered if r.error)
    return {
        "method": f"concurrent_w{max_workers}", "count": len(candidates),
        "total_sec": round(elapsed, 3),
        "claims_per_sec": round(claims / elapsed, 3) if elapsed else 0,
        "claims_extracted": claims, "errors": errors,
    }


def bench_identifier_profile(identifier, model):
    from NAE.pipeline.tsu import builder as builder_mod
    from NAE.pipeline.tsu import parser
    start = time.monotonic()
    t0 = time.monotonic()
    candidates = parser.build_candidates(identifier)
    parse_sec = time.monotonic() - t0
    t0 = time.monotonic()
    result = builder_mod.build_tsu_for_identifier(
        identifier, model=model, checkpoint_every=len(candidates)
    )
    llm_sec = time.monotonic() - t0
    total_sec = time.monotonic() - start
    return {
        "identifier": identifier, "candidates_total": len(candidates),
        "claims_extracted": result["report"]["claims_extracted"],
        "parse_sec": round(parse_sec, 2), "llm_sec": round(llm_sec, 2),
        "total_sec": round(total_sec, 2),
        "llm_pct": round(llm_sec / total_sec * 100, 1) if total_sec else 0,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--embed-count", type=int, default=32)
    parser.add_argument("--claim-count", type=int, default=16)
    parser.add_argument("--identifier", type=str, default=None)
    parser.add_argument("--embed-model", default=embed_config.DEFAULT_EMBED_MODEL)
    parser.add_argument("--claim-model", default=tsu_config.DEFAULT_CLAIM_MODEL)
    parser.add_argument("--output", type=str, default=None)
    args = parser.parse_args()

    print("=" * 60)
    print("DBMA 고처리량 통합 - baseline 측정")
    print("=" * 60)

    sys_info = _system_info()
    ollama_info = _ollama_server_info()
    print(f"\n[시스템] RAM={sys_info['ram_gb']}GB CPUs={sys_info['cpus']}")
    print(f"[Ollama] parallel={ollama_info['parallel']} ({ollama_info['raw']})")

    # Bench 1: Embedding
    print("\n[1/3] 임베딩 단건 vs 배치 측정 ...")
    cache_root = _tmp_cache_root()
    test_texts = [f"신학적 문장 테스트 {i}: 교리와 신앙 고백에 관한 내용입니다." for i in range(args.embed_count)]
    single_emb = bench_embedding_single(test_texts, cache_root, args.embed_model)
    batch_emb = bench_embedding_batch(test_texts, cache_root, args.embed_model)
    speedup = batch_emb["texts_per_sec"] / single_emb["texts_per_sec"] if single_emb["texts_per_sec"] else 0
    print(f"  단건: {single_emb['texts_per_sec']:.2f} texts/sec | 배치: {batch_emb['texts_per_sec']:.2f} texts/sec | 속도비: {speedup:.2f}x")

    # Bench 2: Claim extraction
    print("\n[2/3] Claim 추출 단건 vs 동시 측정 ...")
    test_candidates = [
        {"text": f"신학적 주장 문장 테스트 {i}: 이 문장은 독립적인 신학적 의미를 담고 있습니다.",
         "context_before": "앞 문맥 테스트", "context_after": "뒤 문맥 테스트",
         "candidate_scriptures": [], "candidate_citations": []}
        for i in range(args.claim_count)
    ]
    single_claim = bench_claim_single(test_candidates, args.claim_model)
    concurrent_claim = bench_claim_concurrent(test_candidates, args.claim_model, max_workers=4)
    claim_speedup = concurrent_claim["claims_per_sec"] / single_claim["claims_per_sec"] if single_claim["claims_per_sec"] else 0
    print(f"  단건: {single_claim['claims_per_sec']:.3f} claims/sec | 동시(4): {concurrent_claim['claims_per_sec']:.3f} claims/sec | 속도비: {claim_speedup:.2f}x")

    # Bench 3: Identifier profile
    profile = None
    if args.identifier:
        print(f"\n[3/3] identifier='{args.identifier}' 프로파일 ...")
        profile = bench_identifier_profile(args.identifier, args.claim_model)
        print(f"  candidates={profile['candidates_total']} claims={profile['claims_extracted']} "
              f"parse={profile['parse_sec']}s llm={profile['llm_sec']}s total={profile['total_sec']}s "
              f"(LLM 비중 {profile['llm_pct']}%)")

    # Output
    output = args.output or str(Path("docs/perf/HIGH_THROUGHPUT_BASELINE_v1.md"))
    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "system": sys_info, "ollama_server": ollama_info,
        "embedding": {"single": single_emb, "batch": batch_emb, "speedup": round(speedup, 2)},
        "claim_extraction": {"single": single_claim, "concurrent_w4": concurrent_claim, "speedup": round(claim_speedup, 2)},
        "identifier_profile": profile,
    }

    md_lines = [
        "# DBMA 고처리량 통합 - Baseline 측정",
        f"\n**측정일**: {report['timestamp']}",
        f"\n## 시스템\n- RAM: {sys_info['ram_gb']}GB\n- CPUs: {sys_info['cpus']}",
        f"\n## Ollama 서버\n- parallel (-np): {ollama_info['parallel']}\n- 상세: {ollama_info['raw']}",
        f"\n## 임베딩 측정 (batch_size={args.embed_count})",
        "| 방법 | texts/sec | 총시간(s) | 오류 |\n|------|-----------|-----------|------|",
        f"| 단건 | {single_emb['texts_per_sec']:.2f} | {single_emb['total_sec']} | {single_emb['errors']} |",
        f"| 배치 | {batch_emb['texts_per_sec']:.2f} | {batch_emb['total_sec']} | {batch_emb['errors']} |",
        f"\n**배치 속도비**: {speedup:.2f}x",
        f"\n## Claim 추출 측정 (candidates={args.claim_count})",
        "| 방법 | claims/sec | 총시간(s) | 추출 | 오류 |\n|------|------------|-----------|------|------|",
        f"| 단건 | {single_claim['claims_per_sec']:.3f} | {single_claim['total_sec']} | {single_claim['claims_extracted']} | {single_claim['errors']} |",
        f"| 동시(4) | {concurrent_claim['claims_per_sec']:.3f} | {concurrent_claim['total_sec']} | {concurrent_claim['claims_extracted']} | {concurrent_claim['errors']} |",
        f"\n**동시 속도비**: {claim_speedup:.2f}x",
    ]
    if profile:
        md_lines += [
            f"\n## identifier 프로파일: {profile['identifier']}",
            f"- candidates: {profile['candidates_total']}\n- claims 추출: {profile['claims_extracted']}",
            f"- 파싱: {profile['parse_sec']}s\n- LLM: {profile['llm_sec']}s ({profile['llm_pct']}%)",
            f"- 총: {profile['total_sec']}s",
        ]
    md_lines += [
        f"\n## 게이트 판정 기준",
        "- 임베딩 배치: >=2x 속도비 -> Phase 2 진행 / <2x -> 폐기",
        "- Claim 동시: >=1.5x (서버 -np>=2) 또는 >=1.2x (서버 -np=1) -> Phase 3 진행 / 미만 -> 폐기",
    ]

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"\n[출력] {output_path}")

    json_path = output_path.with_suffix(".json")
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"[JSON] {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
