#!/usr/bin/env python3
"""NAE Retrieval Bridge Probe - isolated feasibility prototype.

Purpose:
    Prove that NAE Qdrant (nae_tsu_v1) can serve as a retrieval source
    for DBMA's Production Retrieval path WITHOUT modifying any production code.

Constraints:
    - Does NOT modify core/retrieval.py or any production module.
    - Does NOT modify ADR-001/003/013 boundaries.
    - NAE Qdrant is read-only (no upsert/delete).
    - Uses isolated temporary namespace only.

This is a READ-ONLY probe script. Run it to verify feasibility.
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path
from typing import Any, Optional


def embed_query(text: str, model: str = "bge-m3:latest") -> list[float]:
    """Embed query using Ollama BGE-M3 - same backend as DBMA core."""
    import urllib.request, json

    url = "http://localhost:11434/api/embeddings"
    payload = json.dumps({"model": model, "prompt": text}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    embedding = body.get("embedding")
    if not embedding:
        raise RuntimeError(f"Ollama 응답에 embedding 필드가 없습니다: {body}")
    if len(embedding) != 1024:
        raise ValueError(f"Embedding dimension mismatch: expected 1024, got {len(embedding)}")
    return embedding


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two vectors (assumed L2-normalized)."""
    assert len(a) == len(b), f"Dimension mismatch: {len(a)} vs {len(b)}"
    dot = sum(x * y for x, y in zip(a, b))
    return dot


def query_nae_qdrant(
    query_vector: list[float],
    collection: str = "nae_tsu_v1",
    top_k: int = 20,
) -> list[dict[str, Any]]:
    """Query NAE Qdrant read-only. Returns raw hit records."""
    from qdrant_client import QdrantClient

    client = QdrantClient(url="http://localhost:7333")
    response = client.query_points(
        collection_name=collection,
        query=query_vector,
        limit=top_k,
        with_payload=True,
    )
    results = []
    for point in response.points:
        results.append({
            "point_id": point.id,
            "score": point.score,
            "payload": point.payload or {},
        })
    return results


def map_nae_to_retrieval_result(hit: dict[str, Any]) -> dict[str, Any]:
    """Map NAE Qdrant payload to a DBMA RetrievalEngine-compatible result dict."""
    p = hit["payload"]
    return {
        "tsu_id": p.get("tsu_id"),
        "score": hit["score"],
        "content": p.get("claim", ""),
        "source_text": p.get("source_text", ""),
        "book": p.get("book", ""),
        "author": p.get("author", ""),
        "verse_mapping": {
            "book_id": p.get("book", ""),
            "chapter": p.get("paragraph", 0),
            "verse_start": p.get("sentence", 0),
        },
        "themes": [p.get("doctrine", "")] if p.get("doctrine") else [],
        "citations": p.get("citations", []),
        "source_id": p.get("source_id", ""),
        "edition_id": p.get("edition_id", ""),
        "work_id": p.get("work_id", ""),
        "metadata_provenance": p.get("metadata_provenance"),
        "review_status": p.get("review_status", ""),
        "quality_score": p.get("llm_score"),
    }


def bridge_query(
    query: str,
    top_k: int = 10,
) -> dict[str, Any]:
    """Execute the full NAE -> DBMA retrieval bridge for a single query."""
    t_start = time.perf_counter()

    t0 = time.perf_counter()
    query_vector = embed_query(query)
    embed_ms = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    hits = query_nae_qdrant(query_vector, top_k=top_k)
    qdrant_ms = (time.perf_counter() - t0) * 1000

    mapped = [map_nae_to_retrieval_result(h) for h in hits]
    total_ms = (time.perf_counter() - t_start) * 1000

    return {
        "query": query,
        "embedding_dimension": len(query_vector),
        "embedding_model": "bge-m3:latest",
        "embed_ms": round(embed_ms, 2),
        "qdrant_ms": round(qdrant_ms, 2),
        "total_ms": round(total_ms, 2),
        "results": mapped,
        "result_count": len(mapped),
    }


def verify_compatibility() -> dict[str, Any]:
    """Verify embedding/dimension/distance compatibility between DBMA and NAE."""
    facts = {}

    from core.config import EMBEDDING_DIMENSION as DBMA_DIM
    facts["dbma_embedding_dimension"] = DBMA_DIM

    from NAE.pipeline.index import config as index_config
    from NAE.pipeline.embed import config as embed_config
    facts["nae_collection"] = index_config.COLLECTION_NAME
    facts["nae_vector_size"] = index_config.VECTOR_SIZE
    facts["nae_embed_model"] = embed_config.DEFAULT_EMBED_MODEL
    facts["nae_embed_dimension"] = embed_config.EMBED_DIMENSION

    from qdrant_client import QdrantClient
    client = QdrantClient(url="http://localhost:7333")
    info = client.get_collection("nae_tsu_v1")
    facts["nae_actual_points"] = info.points_count
    facts["nae_actual_distance"] = str(info.config.params.vectors.distance)
    facts["nae_actual_vector_size"] = info.config.params.vectors.size

    facts["dimension_compatible"] = DBMA_DIM == index_config.VECTOR_SIZE
    facts["model_compatible"] = embed_config.DEFAULT_EMBED_MODEL == "bge-m3:latest"
    facts["distance_compatible"] = str(info.config.params.vectors.distance) == "Cosine"

    return facts


def verify_evidence_integrity(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Check that citation/provenance data survives the bridge."""
    issues = []
    complete_count = 0

    for r in results:
        has_tsu_id = bool(r.get("tsu_id"))
        has_source_id = bool(r.get("source_id"))
        has_work_id = bool(r.get("work_id"))
        has_edition_id = bool(r.get("edition_id"))
        has_citations = bool(r.get("citations"))
        has_provenance = r.get("metadata_provenance") is not None
        has_source_text = bool(r.get("source_text"))

        completeness = sum([has_tsu_id, has_source_id, has_work_id, has_edition_id, has_citations, has_provenance, has_source_text]) / 7

        if completeness >= 0.7:
            complete_count += 1

        if not has_tsu_id:
            issues.append(f"Missing tsu_id")
        if not has_source_id:
            issues.append(f"Missing source_id for {r.get('tsu_id', 'unknown')}")

    return {
        "total_results": len(results),
        "complete_evidence_count": complete_count,
        "evidence_completeness_rate": round(complete_count / max(len(results), 1), 4),
        "issues": issues[:5],
    }


def main() -> None:
    print("=" * 70)
    print("NAE Retrieval Bridge Feasibility Probe")
    print("=" * 70)

    # Phase A: Compatibility Matrix
    print("\n[Phase A] Compatibility Matrix")
    print("-" * 40)
    compat = verify_compatibility()
    for k, v in compat.items():
        print(f"  {k}: {v}")

    all_compat = all([
        compat.get("dimension_compatible", False),
        compat.get("model_compatible", False),
        compat.get("distance_compatible", False),
    ])
    print(f"\n  Compatibility: {'ALL COMPATIBLE' if all_compat else 'INCOMPATIBLE - STOP'}")

    if not all_compat:
        print("\n[STOP] Not all compatibility checks passed. Aborting probe.")
        sys.exit(1)

    # Phase B: Real Retrieval Proof
    print("\n[Phase B] Real Retrieval Proof")
    print("-" * 40)

    test_queries = [
        "What does Paul say about suffering in Romans?",
        "교회에서 장로 직분에 대한 성경적 근거",
        "Grace and faith in justification theology",
    ]

    all_evidence = []
    for i, query in enumerate(test_queries, 1):
        print(f"\n  Query {i}/{len(test_queries)}: {query!r}")
        result = bridge_query(query, top_k=5)

        print(f"    Embedding: {result['embedding_dimension']}d, {result['embed_ms']:.1f}ms")
        print(f"    Qdrant:    {result['qdrant_ms']:.1f}ms")
        print(f"    Total:     {result['total_ms']:.1f}ms")
        print(f"    Results:   {result['result_count']} hits")

        for j, r in enumerate(result["results"], 1):
            tsu_id = r.get("tsu_id", "N/A")
            score = r.get("score", 0)
            claim_preview = (r.get("content", "") or "")[:80]
            source_id = r.get("source_id", "N/A")
            work_id = r.get("work_id", "N/A")
            has_citations = bool(r.get("citations"))
            has_provenance = r.get("metadata_provenance") is not None

            print(f"      [{j}] tsu_id={tsu_id} score={score:.4f}")
            print(f"          claim: {claim_preview}")
            print(f"          source_id={source_id} work_id={work_id[:50] if work_id else 'N/A'}")
            print(f"          citations={'yes' if has_citations else 'no'} provenance={'yes' if has_provenance else 'no'}")

        evidence = verify_evidence_integrity(result["results"])
        print(f"    Evidence integrity: {evidence['evidence_completeness_rate']:.1%} complete")
        all_evidence.append((query, result, evidence))

    # Phase C: Summary
    print("\n[Phase C] Summary")
    print("-" * 40)

    total_queries = len(all_evidence)
    avg_latency = sum(r["total_ms"] for _, r, _ in all_evidence) / total_queries
    avg_completeness = sum(e["evidence_completeness_rate"] for _, _, e in all_evidence) / total_queries

    print(f"  Queries tested:      {total_queries}")
    print(f"  Avg latency:         {avg_latency:.1f}ms")
    print(f"  Avg evidence rate:   {avg_completeness:.1%}")

    all_have_results = all(r["result_count"] > 0 for _, r, _ in all_evidence)
    all_complete = all(e["evidence_completeness_rate"] >= 0.7 for _, _, e in all_evidence)

    print(f"  All queries returned results: {all_have_results}")
    print(f"  All evidence complete (>=70%): {all_complete}")

    # Phase D: Verdict
    print("\n[Phase D] Feasibility Verdict")
    print("-" * 40)

    if all_compat and all_have_results and all_complete:
        verdict = "FEASIBLE"
        explanation = (
            "B option is FEASIBLE. NAE Qdrant can serve as a retrieval source "
            "through an adapter path without modifying production code."
        )
    elif all_compat and all_have_results:
        verdict = "PARTIALLY FEASIBLE"
        explanation = (
            "B option is PARTIALLY FEASIBLE. Core compatibility verified but "
            "some evidence fields are incomplete."
        )
    else:
        verdict = "NOT FEASIBLE"
        explanation = (
            "B option is NOT FEASIBLE. Compatibility or data integrity issues "
            "prevent a clean bridge without production code changes."
        )

    print(f"  Verdict: {verdict}")
    print(f"  Explanation: {explanation}")

    # Phase E: Evidence file
    evidence_file = Path("output/nae_bridge_probe_evidence.json")
    evidence_file.parent.mkdir(parents=True, exist_ok=True)
    evidence_data = {
        "probe_version": "1.0.0",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "compatibility": compat,
        "queries": [
            {
                "query": q,
                "result": r,
                "evidence_integrity": e,
            }
            for q, r, e in all_evidence
        ],
        "verdict": verdict,
    }
    with open(evidence_file, "w", encoding="utf-8") as f:
        json.dump(evidence_data, f, ensure_ascii=False, indent=2)
    print(f"\n  Full evidence saved to: {evidence_file}")

    print("\n" + "=" * 70)
    print("Probe complete.")
    print("=" * 70)


if __name__ == "__main__":
    main()
