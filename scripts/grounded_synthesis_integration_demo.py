#!/usr/bin/env python
"""scripts/grounded_synthesis_integration_demo.py -- Grounded Synthesis P9: Real-Model Demo.

실제 QueryProcessor/HybridQueryProcessor와 실제 Ollama(DEFAULT_GEN_MODEL)를 호출하는
참조 구현. pytest에서는 실행하지 않는다 (GPU/모델 가용성에 의존).

사용법:
    python scripts/grounded_synthesis_integration_demo.py "<질의>"
    python scripts/grounded_synthesis_integration_demo.py      # 골드 쿼리 3건 자동 실행

이 스크립트는 core/retrieval.py, core/hybrid_candidate_pipeline.py를 수정하지 않고
import해서 사용한다.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가 (scripts/ 하위에서 core/ import용)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# DBMA 환경 설정
import os
os.environ.setdefault("USE_INVERTED_INDEX", "true")

from core.retrieval import QueryProcessor, RankedCandidate
from core.hybrid_candidate_pipeline import HybridQueryProcessor
from core.evidence_assembly import QuerySpec, assemble_evidence_pool_with_manifest
from core.evidence_model import Evidence
from core.grounded_answer import assemble_grounded_answer
from core.grounded_claims import bind_claims
from core.grounded_synthesis_input import build_synthesis_input
from core.grounded_citation import check_citation_provenance
from core.config import DEFAULT_GEN_MODEL

# Ollama 호출용
try:
    from ollama import chat as ollama_chat
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False


def run_retrieval(query: str) -> tuple[list[RankedCandidate], int]:
    """실제 HybridQueryProcessor로 검색을 실행하고 RankedCandidate[]를 반환."""
    start = time.perf_counter()
    processor = HybridQueryProcessor()
    response = processor.process(query, k=5)
    elapsed_ms = (time.perf_counter() - start) * 1000

    candidates = list(response.top_k_results)
    return candidates, int(elapsed_ms)


def build_pipeline(
    query: str, candidates: list[RankedCandidate],
) -> tuple:
    """P2~P4: EvidencePool → Manifest → SynthesisInput."""
    # P3: Multi-query assembly (단일 질의 시맨틱)
    qs = QuerySpec(query=query, role="primary", order=0)
    multi_input = [(qs, candidates)]
    pool, manifest = assemble_evidence_pool_with_manifest(multi_input)

    # P4: SynthesisInput
    si = build_synthesis_input(pool, manifest, max_evidence=10)
    return pool, manifest, si


def extract_claims_with_ollama(
    query: str, synthesis_input, pool,
) -> tuple:
    """P5: Ollama로 Claim 추출 (실모델).

    ADR-036 B3 준수: synthesis_input.included_evidence_ids만 사용.
    각 evidence 앞에 [evidence_id: ...]를 명시하여 LLM이 근거를 정확히 식별하도록 함.
    """
    if not OLLAMA_AVAILABLE:
        return [], "ollama_not_available"

    # ADR-036 B3: pool.all() 대신 synthesis_input.included_evidence_ids만 사용
    evidence_texts = []
    for eid in synthesis_input.included_evidence_ids:
        ev = pool.get(eid)
        if ev is None:
            continue
        src = ev.source_file or ev.document_title or "미상"
        evidence_texts.append(f"[evidence_id: {ev.evidence_id}] [출처: {src}]\n{ev.text}")

    context_block = "\n\n---\n\n".join(evidence_texts)

    prompt = (
        "다음 자료들을 읽고 질문에 대한 주장을 추출하세요.\n"
        "각 자료 앞에는 [evidence_id: ...] 표시가 있습니다. 주장의 근거로 삼은 자료의\n"
        "evidence_id를 대괄호 안의 값 그대로(수정하지 말고) 인용하세요.\n\n"
        f"자료:\n{context_block}\n\n"
        f"질문: {query}\n\n"
        "출력 형식: 각 줄을 (claim_text, [evidence_ids]) 형태로 출력하세요.\n"
        "evidence_ids는 위에서 본 [evidence_id: ...] 값을 그대로 써야 합니다.\n"
        "자료가 없으면: (근거 자료 없음, [])\n"
    )

    try:
        response = ollama_chat(
            model=DEFAULT_GEN_MODEL,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.0},  # 결정적 출력
        )
        llm_output = response["message"]["content"]
    except Exception as e:
        return [], f"ollama_error: {e}"

    # LLM 출력을 raw_claims로 파싱
    raw_claims = parse_llm_claims(llm_output, pool)
    claims = bind_claims(raw_claims, synthesis_input)
    return claims, "ok"


def parse_llm_claims(llm_output: str, pool) -> list[tuple[str, list[str]]]:
    """Ollama 출력을 (claim_text, [evidence_ids]) 쌍으로 파싱.

    프롬프트가 [evidence_id: X] 형식으로 ID를 제공하므로, 해당 패턴도 함께 추출.
    실제 evidence_id 포맷(NAE-TSU-..., TSU-UNK-..._chunk_..., NAE-UNC-..._p... 등)을 넓게 커버.
    """
    raw_claims: list[tuple[str, list[str]]] = []

    if "근거 자료 없음" in llm_output or "no evidence" in llm_output.lower():
        return [("근거 자료가 없습니다.", [])]

    import re

    # 1) 프롬프트에서 본 [evidence_id: X] 패턴 우선 추출 (non-greedy, 쉼표/공백에서 끊음)
    evidence_id_patterns = re.findall(r'evidence_id:\s*([^\],\s]+(?:_[^,\]\s]+)*)', llm_output)
    # 2) 기존 TSU/NAE 포맷도 함께 추출 (LLM이 다른 형식으로 썼을 경우 대비)
    tsu_ids = re.findall(r'(?:NAE-)?TSU[-_]?(?:UNK[-_])?\w+|NAE-UNC-\w+', llm_output)
    # 3) 대괄호 안의 ID 추출 (예: ['Fuller_Complete_Works_Vol08', 'Hiscox_Standard_Manual'])
    bracket_ids = re.findall(r"\[\s*(['\"])(.*?)\1\s*\]", llm_output)

    # 모든 후보를 합치고 중복 제거 (순서 유지)
    all_candidates: list[str] = []
    seen: set[str] = set()
    for src in evidence_id_patterns + tsu_ids + [b[1] for b in bracket_ids]:
        s = src.strip()
        if s and s not in seen:
            all_candidates.append(s)
            seen.add(s)

    unique_ids = all_candidates

    # 첫 줄을 claim text로 사용
    first_line = llm_output.strip().split("\n")[0]
    if len(first_line) >= 5 and unique_ids:
        raw_claims.append((first_line, unique_ids))
    elif len(first_line) >= 5:
        raw_claims.append((first_line, []))

    return raw_claims


def run_full_pipeline(query: str) -> dict:
    """P1~P7 전체 파이프라인을 실제 모델로 실행."""
    result = {"query": query, "stages": {}}

    # P1: Retrieval
    t0 = time.perf_counter()
    candidates, retrieval_ms = run_retrieval(query)
    result["stages"]["retrieval"] = {
        "candidate_count": len(candidates),
        "latency_ms": retrieval_ms,
        "top_candidate_tsu_id": candidates[0].tsu_id if candidates else None,
        "top_candidate_content_preview": candidates[0].content[:100] if candidates else None,
    }

    # P2~P4: EvidencePool + Manifest + SynthesisInput
    pool, manifest, si = build_pipeline(query, candidates)
    result["stages"]["evidence_pool"] = {
        "pool_size": len(pool),
        "included_evidence_ids": si.included_evidence_ids,
        "truncated": si.truncated,
    }

    # P5: Claim extraction (real model)
    t1 = time.perf_counter()
    claims, claim_status = extract_claims_with_ollama(query, si, pool)
    elapsed_p5 = (time.perf_counter() - t1) * 1000
    result["stages"]["claim_extraction"] = {
        "status": claim_status,
        "latency_ms": elapsed_p5,
        "claim_count": len(claims),
        "claims": [
            {"claim_id": f"claim_{i:03d}", "text": c.text, "evidence_ids": c.evidence_ids, "valid": c.valid}
            for i, c in enumerate(claims)
        ],
    }

    # P6: GroundedAnswer
    ga = assemble_grounded_answer(claims, si)
    result["stages"]["grounded_answer"] = {
        "status": ga.status,
        "insufficiency_reason": ga.insufficiency_reason,
        "text_preview": ga.text[:200] if ga.text else "",
    }

    # P7: CitationCheckResult
    report = check_citation_provenance(ga, si, pool)
    result["stages"]["citation_check"] = {
        "total_checks": report.total_checks,
        "all_passed": report.all_passed,
        "id_missing_count": report.id_missing_count,
        "span_not_found_count": report.span_not_found_count,
        "provenance_untraceable_count": report.provenance_untraceable_count,
        "results": [
            {
                "claim_id": r.claim_id,
                "evidence_id": r.evidence_id,
                "id_exists": r.id_exists,
                "span_found_in_text": r.span_found_in_text,
                "provenance_traceable": r.provenance_traceable,
            }
            for r in report.results
        ],
    }

    return result


def print_result(result: dict) -> None:
    """결과를 사람이 읽을 수 있는 형태로 출력."""
    query = result["query"]
    print("=" * 70)
    print(f"QUERY: {query}")
    print("=" * 70)

    # Retrieval
    r = result["stages"]["retrieval"]
    print(f"\n[P1 Retrieval]")
    print(f"  Candidates: {r['candidate_count']}")
    print(f"  Latency: {r['latency_ms']:.1f}ms")
    if r["top_candidate_tsu_id"]:
        print(f"  Top TSU: {r['top_candidate_tsu_id']}")
        print(f"  Preview: {r['top_candidate_content_preview']}...")

    # Evidence Pool
    ep = result["stages"]["evidence_pool"]
    print(f"\n[P2-P4 EvidencePool + SynthesisInput]")
    print(f"  Pool size: {ep['pool_size']}")
    print(f"  Included IDs: {ep['included_evidence_ids']}")
    print(f"  Truncated: {ep['truncated']}")

    # Claims
    ce = result["stages"]["claim_extraction"]
    print(f"\n[P5 Claim Extraction]")
    print(f"  Status: {ce['status']}")
    print(f"  Latency: {ce['latency_ms']:.1f}ms")
    print(f"  Claims: {ce['claim_count']}")
    for c in ce["claims"]:
        print(f"    - [{c['claim_id']}] valid={c['valid']} ids={c['evidence_ids']}")
        print(f"      text={c['text'][:80]}...")

    # Grounded Answer
    ga = result["stages"]["grounded_answer"]
    print(f"\n[P6 GroundedAnswer]")
    print(f"  Status: {ga['status']}")
    print(f"  Reason: {ga['insufficiency_reason']}")
    print(f"  Text: {ga['text_preview']}...")

    # Citation Check
    cc = result["stages"]["citation_check"]
    print(f"\n[P7 CitationCheckResult]")
    print(f"  Total checks: {cc['total_checks']}")
    print(f"  All passed: {cc['all_passed']}")
    for r in cc["results"]:
        print(f"    - [{r['claim_id']}]->[{r['evidence_id']}] "
              f"id={r['id_exists']} span={r['span_found_in_text']} prov={r['provenance_traceable']}")

    print("\n" + "=" * 70)


# ============================================================
# Gold queries from docs/NAE_GOLD_QUERY_SET_P0_5_001.md
# ============================================================

GOLD_QUERIES = [
    # G2: 근거 부족 경로 (조작된 인물)
    '"존 스미스 3세"라는 신학자가 주장했다는 교회론의 핵심 내용은 무엇입니까?',
    # A1: 본문 주해 (코퍼스에서 다룰 가능성 있음)
    '로마서 8:1-4은 그리스도인의 정죄 없음에 대해 무엇을 말합니까?',
    # B1: 교리 질문
    '유아세례가 아니라 신자의 침례(believer\'s baptism)를 주장하는 성경적·신학적 근거는 무엇입니까?',
]


def main():
    """메인 실행 경로."""
    queries = GOLD_QUERIES

    # CLI 인자가 있으면 그것만 실행
    if len(sys.argv) > 1:
        queries = [sys.argv[1]]

    all_results = []
    for i, query in enumerate(queries, 1):
        print(f"\n\n>>> Query {i}/{len(queries)}: {query}")
        result = run_full_pipeline(query)
        all_results.append(result)
        print_result(result)

    # JSON 결과도 stdout에 출력 (파일 기록용)
    print("\n\n=== JSON RESULTS ===")
    print(json.dumps(all_results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
