"""Clean rebuild nae_ref_v1 collection with deterministic ID fix.

Fixes: uuid5(REF_NAMESPACE, f"{identifier}:{chunk_index}") — volume-unique IDs.
Order: Vol01 → Vol02 → Vol03 → Vol04 (no collision possible).
"""
import hashlib
import uuid
import time
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance
from NAE.pipeline.reference import chunker
from NAE.pipeline.embed import client as embed_client

REF_NAMESPACE = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")


def create_collection(client: QdrantClient) -> None:
    """Create nae_ref_v1 collection with bge-m3 vector size (1024)."""
    client.create_collection(
        collection_name="nae_ref_v1",
        vectors_config=VectorParams(size=1024, distance=Distance.COSINE),
    )
    print("  Created nae_ref_v1 collection (1024-dim, COSINE)")


def ingest_volume(client: QdrantClient, vol: int) -> dict:
    """Ingest one volume into nae_ref_v1 with deterministic IDs."""
    canonical_path = Path(
        f"NAE/corpus/canonical/Smith_Bible_Dictionary_HackettAbbot_Vol{vol}/canonical.json"
    )
    identifier = f"Smith_Bible_Dictionary_HackettAbbot_Vol{vol}"
    source_id = f"BAP-REF-SMITH-VOL{vol:02d}"
    volume = f"vol_{vol}"

    print(f"\n=== Ingesting Vol{vol} ===")
    start_all = time.time()

    canonical = chunker.load_canonical(canonical_path)
    chunks = chunker.chunk_canonical(canonical, chunk_size=512, chunk_overlap=64)
    print(f"  Chunks: {len(chunks)}")

    points = []
    embedded = 0
    errors = []

    for i, chunk in enumerate(chunks):
        content_hash = hashlib.sha256(chunk.text.encode("utf-8")).hexdigest()
        vector = embed_client.embed_text(
            chunk.text, content_hash=content_hash, model="bge-m3"
        )
        if vector is None:
            errors.append(f"Chunk {i}: embedding failed")
            continue

        # FIX: identifier 포함 — volume-unique ID
        point_id = uuid.uuid5(REF_NAMESPACE, f"{identifier}:{i}").hex
        payload = {
            "chunk_index": chunk.chunk_index,
            "text": chunk.text,
            "identifier": identifier,
            "source_id": source_id,
            "volume": volume,
            "page_start": chunk.page_start,
            "page_end": chunk.page_end,
            "heading_context": chunk.heading_context,
            "content_type": "reference_dictionary",
        }
        points.append(PointStruct(id=point_id, vector=vector, payload=payload))
        embedded += 1

        if len(points) >= 100:
            client.upsert(collection_name="nae_ref_v1", points=points)
            print(f"  Upserted batch {len(points)} (total: {embedded})")
            points = []

    if points:
        client.upsert(collection_name="nae_ref_v1", points=points)
        print(f"  Upserted final batch {len(points)} (total: {embedded})")

    elapsed = time.time() - start_all
    info = client.get_collection("nae_ref_v1")
    print(f"  Vol{vol} complete: {embedded} embedded, {len(errors)} errors in {elapsed:.1f}s")
    print(f"  Collection total points: {info.points_count}")

    return {"chunks": len(chunks), "embedded": embedded, "errors": len(errors)}


if __name__ == "__main__":
    client = QdrantClient(url="http://localhost:7333")

    # Clean start
    try:
        client.delete_collection("nae_ref_v1")
        print("Deleted existing nae_ref_v1 collection.")
    except Exception:
        pass

    create_collection(client)

    results = {}
    for vol in [1, 2, 3, 4]:
        results[vol] = ingest_volume(client, vol)

    final_info = client.get_collection("nae_ref_v1")
    total_expected = sum(r["embedded"] for r in results.values())
    print(f"\n=== Rebuild Complete ===")
    print(f"Total expected: {total_expected}")
    print(f"Actual points:  {final_info.points_count}")
    print(f"Match: {'✓' if total_expected == final_info.points_count else '✗ MISMATCH'}")

    for vol in [1, 2, 3, 4]:
        r = results[vol]
        print(f"  Vol{vol}: {r['chunks']} chunks, {r['embedded']} embedded, {r['errors']} errors")