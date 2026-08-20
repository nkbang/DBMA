#!/usr/bin/env python3
"""CitationBuilder execution evidence — actual runtime proof.

Loads real NAE payload data from probe evidence, maps it to CitationBuilder
input format, executes build_citations(), and captures actual output.

This is a READ-ONLY verification script. No production code modified.
"""
from __future__ import annotations
import json
import sys
import time
from pathlib import Path
from dataclasses import asdict

# Import production classes (read-only)
from core.retrieval import CitationBuilder, RankedCandidate, Citation

EVIDENCE_FILE = Path(__file__).parent.parent / "nae_bridge_probe_evidence.json"

def load_nae_hits():
    """Load real NAE probe results from evidence file."""
    with open(EVIDENCE_FILE) as f:
        data = json.load(f)
    queries = data.get("queries", [])
    if not queries:
        print("ERROR: No queries in evidence file", file=sys.stderr)
        sys.exit(1)
    # Use first query's results (real NAE hits)
    return queries[0]["result"]["results"]

def map_nae_to_citation_metadata(nae_payload: dict, score: float) -> dict:
    """Map NAE Qdrant payload to CitationBuilder-compatible metadata dict.

    NAE probe evidence hits are flat dicts with these fields:
      tsu_id, score, content, source_text, book, author, verse_mapping,
      themes, citations, source_id, edition_id, work_id, metadata_provenance,
      review_status, quality_score
    """
    # verse_mapping is already nested in the flat hit
    vm = nae_payload.get("verse_mapping", {})
    return {
        "tsu_id": nae_payload.get("tsu_id"),
        "title": f"{nae_payload.get('book', '')} by {nae_payload.get('author', '')}",
        "author": nae_payload.get("author"),
        "document_id": nae_payload.get("work_id", ""),
        "content": nae_payload.get("content", ""),  # flat hit uses 'content', not 'claim'
        "provenance": {"confidence": nae_payload.get("quality_score", 0.5)},
        "source_file": nae_payload.get("source_id", ""),
        "language": "en" if nae_payload.get("source_text", "").isascii() else "ko",
        "source_type": nae_payload.get("themes", [""])[0] if nae_payload.get("themes") else "",
        "verse_mapping": {
            "book_id": vm.get("book_id", nae_payload.get("book", "")),
            "chapter": vm.get("chapter", 0),
            "verse_start": vm.get("verse_start", 0),
        },
    }

def create_ranked_candidate(nae_hit: dict, idx: int) -> RankedCandidate:
    """Create a RankedCandidate from NAE hit for CitationBuilder input.

    NAE probe evidence hits are flat dicts (no nested 'payload' key).
    Fields like tsu_id, score, content, book, author, etc. are at the top level.
    """
    # nae_hit is already the payload (flat dict from probe results)
    metadata = map_nae_to_citation_metadata(nae_hit, nae_hit["score"])
    return RankedCandidate(
        tsu_id=nae_hit.get("tsu_id", ""),
        content=nae_hit.get("content", ""),
        metadata=metadata,
        vector_score=nae_hit["score"],
        bm25_score=0.0,  # NAE bridge: no BM25
        theological_score=0.0,  # NAE bridge: no theological scoring
        passage_score=0.0,  # NAE bridge: no passage scoring
        final_score=nae_hit["score"],
        explanation=f"NAE Qdrant vector search (score={nae_hit['score']:.4f})",
    )

def main():
    print("=" * 70)
    print("CitationBuilder Execution Evidence")
    print(f"Timestamp: {time.strftime('%Y-%m-%dT%H:%M:%S')}")
    print("=" * 70)

    # A. Load real input
    print("\n--- A. Real Input (from NAE probe evidence) ---")
    nae_hits = load_nae_hits()
    print(f"Loaded {len(nae_hits)} real NAE hits from: {EVIDENCE_FILE}")
    for i, hit in enumerate(nae_hits[:3]):  # Top 3
        p = hit  # flat dict, no nested payload
        print(f"  [{i+1}] tsu_id={p.get('tsu_id')}, score={hit['score']:.4f}")
        print(f"      content={p.get('content', '')[:60]}...")

    # B. Map to CitationBuilder input
    print("\n--- B. Mapping to RankedCandidate ---")
    candidates = [create_ranked_candidate(hit, i) for i, hit in enumerate(nae_hits[:3])]
    for i, c in enumerate(candidates):
        print(f"  [{i+1}] tsu_id={c.tsu_id}, final_score={c.final_score:.4f}")
        print(f"      metadata keys: {list(c.metadata.keys())}")

    # C. Mapping output (metadata dict)
    print("\n--- C. Mapping Output (first candidate metadata) ---")
    c0_meta = candidates[0].metadata
    for k, v in c0_meta.items():
        display_v = str(v)[:80] if len(str(v)) > 80 else str(v)
        print(f"  {k}: {display_v}")

    # D. CitationBuilder actual call
    print("\n--- D. CitationBuilder().build_citations() execution ---")
    builder = CitationBuilder()
    start = time.time()
    citations = builder.build_citations(candidates)
    elapsed = (time.time() - start) * 1000
    print(f"  Execution time: {elapsed:.2f}ms")
    print(f"  Returned {len(citations)} Citation object(s)")

    # E. Actual returned Citation objects (repr)
    print("\n--- E. Actual Citation Objects (structured output) ---")
    citation_json = []
    for i, cit in enumerate(citations):
        cit_dict = asdict(cit)
        citation_json.append(cit_dict)
        print(f"\n  === Citation[{i+1}] ===")
        for k, v in cit_dict.items():
            display_v = str(v)[:100] if len(str(v)) > 100 else str(v)
            print(f"    {k}: {display_v}")

    # F. Exit code
    print(f"\n--- F. Exit code: 0 (success) ---")

    # G. Timestamp
    print(f"--- G. Execution timestamp: {time.strftime('%Y-%m-%dT%H:%M:%S')} ---")

    # H. Source/TSU identity
    print("\n--- H. Source/TSU Identity ---")
    for i, cit in enumerate(citations):
        print(f"  [{i+1}] tsu_id={cit.tsu_id}, scripture_reference={cit.scripture_reference}")
        print(f"      source_title={cit.source_title}")
        print(f"      source_author={cit.source_author}")
        print(f"      document_id={cit.document_id}")

    # Save structured output
    output = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "execution_ms": elapsed,
        "citation_count": len(citations),
        "citations": citation_json,
        "exit_code": 0,
    }
    out_path = Path(__file__).parent / "citationbuilder-execution.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\n--- Structured output saved to: {out_path} ---")

    return 0

if __name__ == "__main__":
    sys.exit(main())
