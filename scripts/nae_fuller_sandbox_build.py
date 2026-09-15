"""Build / refresh the isolated Fuller sandbox retrieval collection.

Embeds selected Fuller volumes' TSU `claim` fields (bge-m3, the production
embed path via embed_client.embed_text keyed by compute_content_hash) and
upserts them into `nae_tsu_fuller_sandbox_v0` on the NAE Qdrant (:7333).

ISOLATED: never touches `nae_tsu_v1` / `nae_ref_v1`. Not F4/F5 (Amendment A
governs those into `nae_tsu_v1`). `review_status` stays `generated`; CJK
contamination is left as-is until `nae_fuller_cjk_reextract` runs post-F2.

Usage:
  python -m scripts.nae_fuller_sandbox_build --identifiers Vol01,Vol02        # rebuild those
  python -m scripts.nae_fuller_sandbox_build --identifiers Vol01,Vol02 --recreate
"""
from __future__ import annotations

import argparse
import sys
import time
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from NAE.pipeline.embed import client as embed_client  # noqa: E402
from NAE.pipeline.ingest.content_hash import compute_content_hash  # noqa: E402
import json  # noqa: E402
from qdrant_client import QdrantClient  # noqa: E402
from qdrant_client.models import Distance, VectorParams, PointStruct  # noqa: E402

TSU_ROOT = REPO_ROOT / "NAE" / "corpus" / "tsu"
QDRANT_URL = "http://localhost:7333"
COLL = "nae_tsu_fuller_sandbox_v0"
DIM = 1024
PROTECTED = {"nae_tsu_v1", "nae_ref_v1"}


def _load(identifier: str) -> list[dict]:
    p = TSU_ROOT / f"Fuller_Complete_Works_{identifier}" / "tsu.json"
    if not p.exists():
        raise SystemExit(f"missing {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--identifiers", required=True, help="comma list, e.g. Vol01,Vol02")
    ap.add_argument("--recreate", action="store_true", help="drop and recreate the collection first")
    args = ap.parse_args(argv)

    assert COLL not in PROTECTED
    idents = [x.strip() for x in args.identifiers.split(",") if x.strip()]
    client = QdrantClient(url=QDRANT_URL, timeout=60)

    if args.recreate and client.collection_exists(COLL):
        client.delete_collection(COLL)
    if not client.collection_exists(COLL):
        client.create_collection(COLL, vectors_config=VectorParams(size=DIM, distance=Distance.COSINE))
        print(f"[sandbox] created {COLL}")

    total_up = 0
    for ident in idents:
        recs = _load(ident)
        # clear any prior points for this volume (idempotent rebuild)
        from qdrant_client import models as qm
        client.delete(COLL, points_selector=qm.FilterSelector(filter=qm.Filter(
            must=[qm.FieldCondition(key="volume", match=qm.MatchValue(value=ident))])))
        pts, miss = [], 0
        t0 = time.monotonic()
        for i, r in enumerate(recs, 1):
            h = compute_content_hash(r)
            if embed_client.get_cached(h) is None:
                miss += 1
            v = embed_client.embed_text(r["claim"], content_hash=h)
            if v is None:
                continue
            pts.append(PointStruct(id=str(uuid.uuid4()), vector=v, payload={
                "tsu_id": r["id"], "volume": ident, "claim": r["claim"],
                "claim_raw": r.get("claim_raw"), "cjk_status": r.get("cjk_status"),
                "source_text": r.get("source_text"), "doctrine": r.get("doctrine"),
                "book": r.get("book"), "page": r.get("page"),
                "scriptures": r.get("scriptures", []), "confidence": r.get("confidence"),
            }))
            if i % 500 == 0:
                print(f"  [{ident}] {i}/{len(recs)} | fresh={miss} | {time.monotonic()-t0:.0f}s")
        for j in range(0, len(pts), 256):
            client.upsert(COLL, points=pts[j:j + 256])
        total_up += len(pts)
        print(f"[sandbox] {ident}: upserted {len(pts)} ({miss} freshly embedded, {time.monotonic()-t0:.0f}s)")

    info = client.get_collection(COLL)
    print(f"[sandbox] {COLL} now holds {info.points_count} points")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
