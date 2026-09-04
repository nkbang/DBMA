"""Quick apply script for Smith's Bible Dictionary Vol01 reference ingestion."""
import json
import hashlib
import logging
import sys
import uuid
from pathlib import Path

# Add repo root to path for NAE imports
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import ollama
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("nae.reference.apply")

# ── Config ──────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
CANONICAL_PATH = REPO_ROOT / "NAE" / "corpus" / "canonical" / "Smith_Bible_Dictionary_HackettAbbot_Vol1" / "canonical.json"
QDRANT_URL = "http://localhost:7333"
COLLECTION_NAME = "nae_ref_v1"
CHUNK_SIZE = 1200
CHUNK_OVERLAP = 200
IDENTIFIER = "Smith_Bible_Dictionary_HackettAbbot_Vol1"
SOURCE_ID = "BAP-REF-SMITH-VOL01"
VOLUME = "vol_1"
REF_NAMESPACE = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")


def chunk_canonical(paragraphs: list[dict]) -> list[str]:
    """Simple linear chunking (mirrors chunker.py logic)."""
    chunks: list[str] = []
    current_heading: str = ""
    buf_text: list[str] = []
    buf_len: int = 0

    def _flush(carry_overlap: bool = False) -> None:
        nonlocal buf_text, buf_len, current_heading
        if not buf_text:
            return
        text = "\n\n".join(buf_text).strip()
        if current_heading:
            text = f"[{current_heading}]\n\n{text}"
        chunks.append(text)
        if carry_overlap and len(buf_text) >= 2:
            ov = buf_text[-1][:CHUNK_OVERLAP] if len(buf_text[-1]) > CHUNK_OVERLAP else buf_text[-1]
            buf_text = [ov]
            buf_len = len(ov)
        else:
            buf_text = []
            buf_len = 0

    for para in paragraphs:
        ptype = para.get("type", "prose")
        txt = para.get("text", "")
        if not txt or not txt.strip():
            continue
        if ptype == "heading":
            _flush(carry_overlap=False)
            current_heading = txt.strip()
            continue
        next_len = buf_len + (2 if buf_text else 0) + len(txt)
        if buf_text and next_len > CHUNK_SIZE:
            _flush(carry_overlap=True)
        buf_text.append(txt)
        buf_len = len("\n\n".join(buf_text))
    _flush(carry_overlap=False)
    return chunks


def main() -> None:
    # 1. Load canonical
    logger.info("Loading canonical: %s", CANONICAL_PATH)
    d = json.loads(CANONICAL_PATH.read_text(encoding="utf-8"))
    paragraphs = d.get("paragraphs", [])
    logger.info("Canonical has %d paragraphs", len(paragraphs))

    # 2. Chunk
    chunks = chunk_canonical(paragraphs)
    logger.info("Generated %d chunks", len(chunks))

    # 3. Connect to Qdrant
    client = QdrantClient(url=QDRANT_URL)
    existing = {c.name for c in client.get_collections().collections}
    if COLLECTION_NAME not in existing:
        logger.info("Creating collection %s", COLLECTION_NAME)
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=1024, distance=Distance.COSINE),
        )

    # 4. Embed + upsert
    from NAE.pipeline.embed import client as embed_client

    for i, text in enumerate(chunks):
        content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()

        cached = embed_client.get_cached(content_hash)
        if cached is not None:
            vector = cached
        else:
            try:
                result = ollama.embeddings(model="bge-m3:latest", prompt=text)
                vector = result["embedding"]
                embed_client._save_cache(content_hash, vector)
            except Exception as e:
                logger.warning("Embed failed chunk %d: %s", i, e)
                continue

        point_id = uuid.uuid5(REF_NAMESPACE, str(i)).hex
        payload = {
            "chunk_index": i,
            "text": text,
            "identifier": IDENTIFIER,
            "source_id": SOURCE_ID,
            "volume": VOLUME,
            "content_type": "reference_dictionary",
        }

        client.upsert(
            collection_name=COLLECTION_NAME,
            points=[PointStruct(id=point_id, vector=vector, payload=payload)],
        )

        if (i + 1) % 500 == 0:
            info = client.get_collection(COLLECTION_NAME)
            logger.info("Progress: %d/%d chunks, Qdrant points: %d", i + 1, len(chunks), info.points_count)

    info = client.get_collection(COLLECTION_NAME)
    logger.info("Done! Total Qdrant points: %d", info.points_count)


if __name__ == "__main__":
    main()
