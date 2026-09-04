"""Batch ingest Smith Bible Dictionary Vol02-04 into Qdrant (batch upsert)."""
import hashlib
import uuid
import time
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from NAE.pipeline.reference import chunker
from NAE.pipeline.embed import client as embed_client

REF_NAMESPACE = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")


def ingest_volume(vol: int) -> None:
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

    client = QdrantClient(url="http://localhost:7333")

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

    info = client.get_collection("nae_ref_v1")
    elapsed = time.time() - start_all
    print(f"  Vol{vol} complete: {embedded} embedded, {len(errors)} errors in {elapsed:.1f}s")
    print(f"  Collection total points: {info.points_count}")


for vol in [2, 3, 4]:
    ingest_volume(vol)

print("\n=== All volumes ingested ===")
