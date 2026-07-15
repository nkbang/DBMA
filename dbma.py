from __future__ import annotations

import json
import logging
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# ─── SPRINT 2 FEATURE FLAG ───────────────────────────────
# Sprint 1 = False → PURE DATA LAYER ONLY (parse → clean → chunk → store .md)
# Sprint 2+ = True  → Re-enable embedding, vector DB, LLM, RAG
SPRINT2_FEATURES = False  # Set True to enable all features

# ─── FEATURE FLAG HELPER ───────────────────────────────
# Introducing capability-based feature flag system
from core.feature_flags import feature_enabled

if feature_enabled("embedding"):
    import chromadb
    import ollama
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from core.embedder import embed as embed_via_transformer
    from core.md_manager import (
        save_md_with_change_detection,
        _split_by_markdown_headers,
    )
    from core.ingest import insert as ingest_to_qdrant
    from core.qdrant_init import init_collection as qdrant_init_collection
    from core.search import search as search_qdrant_index

import pandas as pd
import streamlit as st

from core.config import (
    APP_NAME, APP_VERSION, CHROMA_COLLECTION, CHROMA_PERSIST_DIR, SUPPORTED_EXTENSIONS,
    DEFAULT_CHUNK_SIZE, DEFAULT_CHUNK_OVERLAP,
    DEFAULT_EMBED_MODEL, DEFAULT_GEN_MODEL, EMBED_MODEL_OPTIONS, GEN_MODEL_OPTIONS,
    DEFAULT_PROGRESS, RAG_MIN_LEN, RAG_MAX_NOISE, RAG_TOP_K, DEFAULT_TEMPERATURE,
    DEFAULT_OUTPUT_DIR, DEFAULT_RAW_DIR,
)
from core.files import scan_directory
from core.processing import build_converter, build_splitter, process_one_file
from core.utils import calculate_noise_score

st.set_page_config(page_title="DBMAr", layout="wide")

if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.INFO)


def safe_log_exception(msg: str):
    try:
        logging.getLogger(__name__).error(msg, exc_info=False)
    except Exception:
        pass


PROJECT_ROOT = Path(__file__).resolve().parent

# config.yaml based directories (all dynamic)
RAW_DIR = PROJECT_ROOT / DEFAULT_RAW_DIR
OUTPUT_DIR = PROJECT_ROOT / DEFAULT_OUTPUT_DIR
DOCS_DIR = PROJECT_ROOT / "docs"
LOGS_DIR = PROJECT_ROOT / "logs"
TODO_MD = DOCS_DIR / "dbmar_todo_progress_board.md"
PROGRESS_CSV = DOCS_DIR / "dbmar_progress_snapshot.csv"
EVENTS_JSONL = LOGS_DIR / "project_events.jsonl"

# Benchmark result paths (output/bench/ isolated folder + docs/ fallback)
BENCH_CSV_BENCH = Path("output/bench") / "benchmark_results.csv"
BENCH_CSV_DOCS = DOCS_DIR / "rag_benchmark.csv"


def get_bench_csv(create_if_missing: bool = False) -> Path:
    """Return benchmark CSV path (output/bench preferred, docs fallback)."""
    if BENCH_CSV_BENCH.exists():
        return BENCH_CSV_BENCH
    if BENCH_CSV_DOCS.exists():
        return BENCH_CSV_DOCS
    if create_if_missing:
        BENCH_CSV_BENCH.parent.mkdir(parents=True, exist_ok=True)
        if not BENCH_CSV_BENCH.exists():
            pd.DataFrame([{
                "ts": "", "embed_model": "", "gen_model": "", "chunk_size": "", "overlap": "",
                "top_k": "", "docs": "", "chunks": "", "question": "", "answer_len": "",
                "elapsed_sec": "", "source_count": "",
            }]).head(0).to_csv(BENCH_CSV_BENCH, index=False)
        return BENCH_CSV_BENCH
    return BENCH_CSV_BENCH


# ChromaDB paths — Sprint 2 only
if feature_enabled("vector_db"):
    CHROMA_DIR = PROJECT_ROOT / CHROMA_PERSIST_DIR
    COLLECTION_NAME = CHROMA_COLLECTION

SUPPORTED_EXTS = SUPPORTED_EXTENSIONS

# EVENT_TO_AREA mapping (business logic)
EVENT_TO_AREA: dict[str, str] = {
    "parse_completed": "멀티 포맷 추출",
    "clean_completed": "텍스트 정제",
    "chunk_completed": "청킹 전략",
    "index_completed": "임베딩/인덱싱",
    "eval_completed": "평가 루프",
    "log_completed": "로그/추적성",
    "ui_completed": "UI/탭 구조",
    "docs_completed": "문서화/운영",
}


def ensure_dirs():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    if feature_enabled("vector_db"):
        CHROMA_DIR.mkdir(parents=True, exist_ok=True)


def _parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML-like frontmatter from markdown content."""
    meta: dict = {}
    body = content
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            for line in parts[1].strip().splitlines():
                if ":" in line:
                    key, value = line.split(":", 1)
                    meta[key.strip()] = value.strip()
            body = parts[2].strip()
    return meta, body


def _save_md_with_metadata(output_dir: str, stem: str, content: str, meta: dict) -> str:
    """Save markdown with metadata (core/md_manager.py integration)."""
    filepath = str(Path(output_dir) / f"{stem}.md")
    if feature_enabled("embedding"):
        changed = save_md_with_change_detection(filepath, content)
    else:
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        Path(filepath).write_text(content, encoding="utf-8")
    return filepath


def _split_content_by_headers(content: str, filepath: str) -> list:
    """Split markdown by header sections (core/md_manager.py integration)."""
    if feature_enabled("embedding"):
        return _split_by_markdown_headers(content, filepath)
    return []


# ═══════════════════════════════════════════════════════════
# SPRINT 1 DISABLED — Embedding functions (ollama backend)
# ═══════════════════════════════════════════════════════════

def embed_text_ollama(texts, model: str = DEFAULT_EMBED_MODEL) -> list:
    """Embed texts using Ollama (SPRINT 1 DISABLED)."""
    if not feature_enabled("embedding"):
        return []
    try:
        return ollama.embed(model=model, input=texts)["embeddings"]
    except Exception as e:
        if "tokenize" in str(e).lower() or len(texts) > 1:
            out = []
            for t in texts:
                if not t.strip():
                    continue
                try:
                    out.extend(ollama.embed(model=model, input=t)["embeddings"])
                except Exception:
                    continue
            if out:
                return out
        raise


def _noise_for_display(result: dict) -> dict:
    score = float(result.get("score", 100.0))
    if score >= 70:
        level, usable = "HIGH", False
    elif score >= 40:
        level, usable = "MEDIUM", True
    elif score >= 15:
        level, usable = "LOW", True
    else:
        level, usable = "GOOD", True
    return {
        "score": score, "level": level, "usable": usable,
        "reason": result.get("mode", "ok"), "metrics": result,
    }


def score_to_color(score: float) -> str:
    if score >= 70:
        return "#e74c3c"
    if score >= 40:
        return "#f39c12"
    if score >= 15:
        return "#f1c40f"
    return "#2ecc71"


def score_to_label(score: float) -> str:
    if score >= 70:
        return "HIGH NOISE"
    if score >= 40:
        return "MEDIUM NOISE"
    if score >= 15:
        return "LOW NOISE"
    return "GOOD"


def append_event(event, status="DONE", delta=5, note="", run_id="manual"):
    ensure_dirs()
    entry = {"event": event, "status": status, "delta": delta, "note": note, "run_id": run_id, "ts": pd.Timestamp.now().isoformat(timespec="seconds")}
    try:
        with EVENTS_JSONL.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        safe_log_exception(f"event write failed: {e}")
    try:
        df = load_progress_df()
        area = EVENT_TO_AREA.get(event)
        if area and area in set(df["영역"]):
            i = df.index[df["영역"] == area][0]
            current = int(df.at[i, "진행률"])
            if status == "DONE":
                current = min(100, current + delta)
                df.at[i, "상태"] = "DONE" if current >= 100 else "DOING"
            else:
                df.at[i, "상태"] = status
            df.at[i, "진행률"] = current
            save_progress_df(df)
            refresh_todo_doc(df)
        return df
    except Exception as e:
        safe_log_exception(f"append_event failed: {e}")
        return load_progress_df()


def load_progress_df():
    ensure_dirs()
    if PROGRESS_CSV.exists():
        try:
            return pd.read_csv(PROGRESS_CSV)
        except Exception:
            pass
    df = pd.DataFrame(DEFAULT_PROGRESS)
    df.to_csv(PROGRESS_CSV, index=False)
    return df


def save_progress_df(df):
    ensure_dirs()
    df.to_csv(PROGRESS_CSV, index=False)


def refresh_todo_doc(df=None):
    try:
        ensure_dirs()
        if df is None:
            df = load_progress_df()
        avg = float(df["진행률"].mean()) if not df.empty else 0.0
        todo = int((df["상태"] == "TODO").sum())
        blocked = int((df["상태"] == "BLOCKED").sum())
        auto = ["", "---", "## Auto Summary", f"- 전체 평균 진행률: {avg:.1f}%", f"- TODO 수: {todo}", f"- BLOCKED 수: {blocked}", "", "### 영역별 상태"]
        for _, row in df.iterrows():
            auto.append(f"- {row['영역']}: {int(row['진행률'])}% / {row['상태']}")
        if TODO_MD.exists():
            base = TODO_MD.read_text(encoding="utf-8").split("\n---\n## Auto Summary")[0].rstrip()
        else:
            base = "# DBMAr Project State\n\n이 파일은 프로젝트 모니터링의 기준 문서입니다."
        TODO_MD.write_text(base + "\n" + "\n".join(auto) + "\n", encoding="utf-8")
    except Exception as e:
        safe_log_exception(f"refresh_todo_doc failed: {e}")


def cleanup_cache():
    """Clear Streamlit cache + splitter cache."""
    for fn in ("clear", "cache_data"):
        obj = getattr(st, fn, None)
        if callable(obj):
            try:
                obj.clear()
            except Exception as e:
                safe_log_exception(f"cleanup_cache {fn} failed: {e}")
    import core.processing as processing
    if hasattr(processing, '_splitter_cache'):
        processing._splitter_cache.clear()


def get_cache_stats():
    ensure_dirs()
    groups = {"md": [], "chunks": [], "other": []}
    for p in OUTPUT_DIR.iterdir():
        if not p.is_file():
            continue
        try:
            size = p.stat().st_size
        except Exception:
            continue
        if p.suffix.lower() == ".md":
            groups["md"].append({"file": p.name, "size": size})
        elif p.name.endswith("_chunks.txt"):
            groups["chunks"].append({"file": p.name, "size": size})
        else:
            groups["other"].append({"file": p.name, "size": size})
    all_items = groups["md"] + groups["chunks"] + groups["other"]
    total_bytes = sum(x["size"] for x in all_items)
    return {
        "count": len(all_items), "bytes": total_bytes,
        "mb": round(total_bytes / (1024 * 1024), 2),
        "md_count": len(groups["md"]), "chunk_count": len(groups["chunks"]),
        "other_count": len(groups["other"]),
        "md_bytes": sum(x["size"] for x in groups["md"]),
        "chunk_bytes": sum(x["size"] for x in groups["chunks"]),
        "other_bytes": sum(x["size"] for x in groups["other"]),
        "items": sorted(all_items, key=lambda x: x["size"], reverse=True),
    }


# ═══════════════════════════════════════════════════════════
# SPRINT 1 DISABLED — ChromaDB vector client helpers
# ═══════════════════════════════════════════════════════════

def get_vector_client():
    """ChromaDB PersistentClient (SPRINT 1 DISABLED)."""
    if not feature_enabled("vector_db"):
        return None
    return chromadb.PersistentClient(path=str(CHROMA_DIR))


def get_collection():
    """Get or create ChromaDB collection (SPRINT 1 DISABLED)."""
    if not feature_enabled("vector_db"):
        return None
    client = get_vector_client()
    if client is None:
        return None
    return client.get_or_create_collection(name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"})


# ═══════════════════════════════════════════════════════════
# SPRINT 1 DISABLED — Embedding/chunking helpers
# ═══════════════════════════════════════════════════════════

def rag_chunk_text(text: str, chunk_size: int = DEFAULT_CHUNK_SIZE, overlap: int = DEFAULT_CHUNK_OVERLAP) -> List[str]:
    """Split document into chunks (SPRINT 1 DISABLED)."""
    if not feature_enabled("embedding"):
        return []
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=overlap, separators=["\n\n", "\n", ". ", " ", ""])
    return splitter.split_text(text or "")


def read_indexable_docs(selected_files: Optional[List[str]] = None, input_dir: str = str(OUTPUT_DIR)) -> List[Dict[str, Any]]:
    """Read .md files with metadata (SPRINT 1 DISABLED — kept for discovery)."""
    if not feature_enabled("embedding"):
        return []
    base = Path(input_dir)
    docs = []
    if not base.exists():
        return docs
    allowed = set(selected_files or [])
    for p in sorted(base.glob("*.md")):
        if allowed and p.name not in allowed:
            continue
        try:
            raw = p.read_text(encoding="utf-8", errors="ignore")
            meta, body = _parse_frontmatter(raw)
            docs.append({
                "source": p.name, "text": body,
                "file_type": meta.get("source_type", "md"),
                "is_ocr": meta.get("noise_mode", "") == "pdf_ocr",
            })
        except Exception:
            pass
    return docs


# ═══════════════════════════════════════════════════════════
# SPRINT 1 DISABLED — Ollama model listing helpers
# ═══════════════════════════════════════════════════════════

def list_ollama_models() -> List[str]:
    """List installed Ollama models (SPRINT 1 DISABLED)."""
    if not feature_enabled("embedding"):
        return []
    try:
        import requests
        r = requests.get("http://localhost:11434/api/tags", timeout=5)
        r.raise_for_status()
        data = r.json()
        return [m.get("name") for m in data.get("models", []) if m.get("name")]
    except Exception:
        return []


def _model_supports_embeddings(model: str) -> bool:
    """Check if model supports embeddings (SPRINT 1 DISABLED)."""
    if not feature_enabled("embedding"):
        return False
    name = (model or "").lower()
    keywords = ["embed", "bge", "nomic", "mxbai", "e5", "snowflake"]
    return any(k in name for k in keywords)


# ═══════════════════════════════════════════════════════════
# SPRINT 1 DISABLED — Qdrant bridge functions
# ═══════════════════════════════════════════════════════════

def _qdrant_available() -> bool:
    """Test if Qdrant is accessible (SPRINT 1 DISABLED)."""
    if not feature_enabled("vector_db"):
        return False
    try:
        from qdrant_client import QdrantClient
        client = QdrantClient("http://localhost:6333", timeout=2)
        client.get_collections()
        return True
    except Exception:
        return False


def _embed_text_qdrant(texts: list, model: str = DEFAULT_EMBED_MODEL) -> list:
    """Embed texts for Qdrant (SPRINT 1 DISABLED)."""
    if not feature_enabled("vector_db"):
        dim = 384
        return [[0.0] * dim for t in texts if t.strip()] if texts else [[0.0] * dim]
    try:
        return _embed_texts(texts, model=model)
    except Exception:
        dim = 384
        return [[0.0] * dim for t in texts if t.strip()] if texts else [[0.0] * dim]


def upsert_to_qdrant(chunks: list, metadatas: list, collection_name: str = "dbma_sermon", embed_model: str = DEFAULT_EMBED_MODEL, url: str = "http://localhost:6333") -> dict:
    """Upsert chunks to Qdrant (SPRINT 1 DISABLED)."""
    if not feature_enabled("vector_db"):
        return {"status": "disabled", "collection": collection_name}
    from qdrant_client import QdrantClient
    from qdrant_client.models import PointStruct, VectorParams, Distance

    client = QdrantClient(url=url)
    existing = {c.name for c in client.get_collections().collections}
    if collection_name not in existing:
        sample_vec = _embed_text_qdrant([chunks[0]], embed_model) if chunks else [0.0] * 768
        client.create_collection(collection_name=collection_name, vectors_config=VectorParams(size=len(sample_vec), distance=Distance.COSINE))

    embeddings = _embed_text_qdrant(chunks, embed_model)
    points = []
    for i, (chunk, meta, emb) in enumerate(zip(chunks, metadatas, embeddings)):
        points.append(PointStruct(
            id=f"{collection_name}::{meta.get('source', 'unknown')}::{i}",
            vector=emb,
            payload={"text": chunk, "source": meta.get("source", "unknown"), "chunk": meta.get("chunk", i), "noise": meta.get("noise", 0.0), "len": meta.get("len", len(chunk))},
        ))
    client.upsert(collection_name=collection_name, points=points)
    return {"upserted": len(points), "collection": collection_name}


def query_qdrant(question: str, top_k: int = RAG_TOP_K, collection_name: str = "dbma_sermon", embed_model: str = DEFAULT_EMBED_MODEL, url: str = "http://localhost:6333", max_noise: float = RAG_MAX_NOISE) -> list:
    """Search Qdrant by vector similarity (SPRINT 1 DISABLED)."""
    if not feature_enabled("vector_db"):
        return []
    from qdrant_client import QdrantClient
    client = QdrantClient(url=url)
    q_emb = _embed_text_qdrant([question], embed_model)[0]
    results = client.query_points(
        collection_name=collection_name,
        query=q_emb,
        limit=top_k,
        with_payload=True,
    ).points
    outputs = []
    for r in results:
        payload = r.payload or {}
        noise = payload.get("noise", 0.0)
        if noise >= max_noise:
            continue
        outputs.append({"score": round(r.score, 4), "text": payload.get("text", ""), "source": payload.get("source", "unknown"), "chunk": payload.get("chunk", 0), "noise": noise})
    return outputs


# ═══════════════════════════════════════════════════════════
# SPRINT 1 DISABLED — Dual backend embedding
# ═══════════════════════════════════════════════════════════

def _embed_texts(texts: List[str], model: str = DEFAULT_EMBED_MODEL) -> List[List[float]]:
    """Batch embedding — Ollama or sentence_transformers (SPRINT 1 DISABLED)."""
    if not feature_enabled("embedding"):
        return []
    try:
        return ollama.embed(model=model, input=texts)["embeddings"]
    except Exception:
        pass
    result = []
    for t in texts:
        if not t.strip():
            continue
        try:
            result.append(embed_via_transformer(t))
        except Exception:
            result.append([0.0] * 384)
    return result


def _rag_noise(text: str, file_type: str = "txt", is_ocr: bool = False) -> float:
    return calculate_noise_score(text, file_type=file_type, is_ocr=is_ocr)["score"]


# ═══════════════════════════════════════════════════════════
# SPRINT 1 DISABLED — RAG store builder (ChromaDB + Qdrant)
# ═══════════════════════════════════════════════════════════

def build_rag_store(selected_files: Optional[List[str]] = None, input_dir: str = str(OUTPUT_DIR), embed_model: str = DEFAULT_EMBED_MODEL, chunk_size: int = DEFAULT_CHUNK_SIZE, overlap: int = DEFAULT_CHUNK_OVERLAP, min_len: int = RAG_MIN_LEN, max_noise: float = RAG_MAX_NOISE, store: str = "both"):
    """Build RAG store (dual-store). SPRINT 1 DISABLED."""
    if not feature_enabled("embedding"):
        return {"documents": 0, "chunks": 0, "indexed": 0, "embed_model": embed_model}
    ensure_dirs()
    docs = read_indexable_docs(selected_files=selected_files, input_dir=input_dir)
    ids, documents, metadatas = [], [], []
    for doc in docs:
        chunks = rag_chunk_text(doc["text"], chunk_size=chunk_size, overlap=overlap)
        for j, chunk in enumerate(chunks):
            if len(chunk.strip()) < min_len:
                continue
            noise = _rag_noise(chunk, file_type=doc.get("file_type", "txt"), is_ocr=doc.get("is_ocr", False))
            if noise >= max_noise:
                continue
            ids.append(f"{doc['source']}::{j}")
            documents.append(chunk)
            metadatas.append({"source": doc["source"], "chunk": j, "noise": noise, "len": len(chunk)})

    result = {"documents": len(docs), "chunks": 0, "indexed": 0, "embed_model": embed_model}
    if not ids:
        result["collection"] = COLLECTION_NAME
        result["chroma_dir"] = str(CHROMA_DIR)
        return result

    if store in ("chroma", "both"):
        collection = get_collection()
        if collection is not None:
            embeddings = _embed_texts(documents, model=embed_model)
            if embeddings:
                collection.upsert(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)  # type: ignore[arg-type]
                result["collection"] = COLLECTION_NAME
                result["chroma_dir"] = str(CHROMA_DIR)

    if store in ("qdrant", "both") and _qdrant_available():
        try:
            result["qdrant"] = upsert_to_qdrant(chunks=documents, metadatas=metadatas, embed_model=embed_model)
        except Exception as e:
            result["qdrant_error"] = str(e)

    result["indexed"] = len(ids)
    result["chunks"] = len(documents)
    return result


# ═══════════════════════════════════════════════════════════
# SPRINT 1 DISABLED — RAG query (retrieval + LLM generation)
# ═══════════════════════════════════════════════════════════

def query_rag(question: str, embed_model: str = DEFAULT_EMBED_MODEL, gen_model: str = DEFAULT_GEN_MODEL, top_k: int = RAG_TOP_K, temperature: float = DEFAULT_TEMPERATURE, max_noise: float = RAG_MAX_NOISE, store: str = "both") -> Dict[str, Any]:
    """RAG query (dual-store). SPRINT 1 DISABLED."""
    if not feature_enabled("rag"):
        return {"question": question, "answer": "[Sprint 1: RAG disabled]", "contexts": [], "sources": [], "embedding_enabled": False, "store_used": []}

    ensure_dirs()
    embedding_enabled = _model_supports_embeddings(embed_model)
    chroma_sources, qdrant_sources, embed_error = [], [], None

    if store in ("chroma", "both") and embedding_enabled:
        q_emb = None
        try:
            all_embs = _embed_texts([question], model=embed_model)
            q_emb = all_embs[0] if all_embs else None
        except Exception as e:
            embed_error = str(e)
            embedding_enabled = False
        if q_emb is not None:
            collection = get_collection()
            if collection is not None:
                queried_results = {"documents": [[]], "metadatas": [[]], "ids": [[]]}
                try:
                    queried_results = collection.query(query_embeddings=[q_emb], n_results=top_k)
                except Exception as e:
                    embed_error = f"{embed_error}; {e}" if embed_error else str(e)
                docs_raw = queried_results.get("documents", [[]])
                metas_raw = queried_results.get("metadatas", [[]])
                ids_raw = queried_results.get("ids", [[]])
                docs = docs_raw[0] if docs_raw and isinstance(docs_raw, list) else []
                metas = metas_raw[0] if metas_raw and isinstance(metas_raw, list) else []
                ids_list = ids_raw[0] if ids_raw and isinstance(ids_raw, list) else []
                for i, doc in enumerate(docs):
                    meta = metas[i] if i < len(metas) else {}
                    source = meta.get("source", "unknown") if isinstance(meta, dict) else "unknown"
                    chunk = meta.get("chunk", i) if isinstance(meta, dict) else i
                    noise_val = meta.get("noise", None) if isinstance(meta, dict) else None
                    if noise_val is not None and (isinstance(noise_val, (int, float)) and noise_val >= max_noise):
                        continue
                    chroma_sources.append({"rank": len(chroma_sources) + 1, "id": ids_list[i] if i < len(ids_list) else "", "source": source, "chunk": chunk, "noise": noise_val, "snippet": doc[:240].replace("\n", " ")})

    if store in ("qdrant", "both") and _qdrant_available():
        try:
            qdrant_sources = query_qdrant(question=question, top_k=top_k, embed_model=embed_model)
            for i, src in enumerate(qdrant_sources):
                src["rank"] = i + 1
        except Exception as e:
            qdrant_err = str(e)

    if chroma_sources:
        filtered_docs = [s.get("snippet", "") for s in chroma_sources]
        all_sources = chroma_sources
        embed_status = "chroma"
    elif qdrant_sources:
        filtered_docs = [s.get("text", "")[:240] for s in qdrant_sources]
        all_sources = qdrant_sources
        embed_status = "qdrant"
    else:
        filtered_docs, all_sources, embed_status = [], [], "none"

    if filtered_docs:
        context = "\n\n".join(filtered_docs)
        prompt = f"문맥:\n{context}\n\n질문:\n{question}"
    else:
        prompt = f"질문:\n{question}"

    answer = ollama.generate(model=gen_model, prompt=prompt, options={"temperature": temperature})["response"]

    status_notes = []
    if embed_status == "none":
        msg = "embedding 검색 비활성화"
        if embed_error:
            msg += f": {embed_error}"
        answer = answer + f"\n\n[주의] {msg}"
    elif embed_status in ("qdrant", "chroma"):
        status_notes.append(embed_status.capitalize())

    return {"question": question, "answer": answer, "contexts": filtered_docs, "sources": all_sources, "embed_model": embed_model, "gen_model": gen_model, "embedding_enabled": embed_status != "none", "embed_error": embed_error, "temperature": temperature, "store_used": status_notes}


def append_benchmark_row(embed_model: str, gen_model: str, chunk_size: int, overlap: int, top_k: int, docs: int, chunks: int, q: str, answer: str, elapsed: float, source_count: int):
    ensure_dirs()
    row = pd.DataFrame([{
        "ts": pd.Timestamp.now().isoformat(timespec="seconds"), "embed_model": embed_model,
        "gen_model": gen_model, "chunk_size": chunk_size, "overlap": overlap, "top_k": top_k,
        "docs": docs, "chunks": chunks, "question": q, "answer_len": len(answer or ""),
        "elapsed_sec": round(elapsed, 3), "source_count": source_count,
    }])
    bench_path = get_bench_csv()
    if bench_path.exists():
        out = pd.concat([pd.read_csv(bench_path), row], ignore_index=True)
    else:
        out = row
    bench_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(bench_path, index=False)


def render_noise_bar(noise: float, usable: bool, level: str):
    color = score_to_color(noise)
    width = max(0, min(100, 100 - int(noise)))
    label = score_to_label(noise)
    usable_text = "사용 가능" if usable else "주의"
    st.markdown(f"""
        <div style="border:1px solid #ddd;border-radius:8px;padding:12px;margin:8px 0;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;"><strong>{label}</strong><span>{usable_text} · noise {noise:.1f}/100</span></div>
            <div style="background:#eee;border-radius:999px;height:14px;overflow:hidden;"><div style="width:{width}%;background:{color};height:14px;"></div></div>
            <div style="margin-top:6px;font-size:0.92em;color:#666;">level: {level}</div>
        </div>
        """, unsafe_allow_html=True)


def init_chat_state():
    for k, v in [("rag_chat", [{"role": "assistant", "content": "안녕하세요. 무엇을 찾고 있나요?"}]), ("rag_input", ""), ("rag_mode", "hybrid"), ("rag_show_context", True)]:
        if k not in st.session_state:
            st.session_state[k] = v


def chat_user_bubble(text: str):
    st.markdown(f'<div style="display:flex;justify-content:flex-end;margin:10px 0;"><div style="max-width:78%;background:linear-gradient(135deg,#6d5efc,#8f7cff);color:white;padding:14px 16px;border-radius:18px 18px 4px 18px;box-shadow:0 8px 24px rgba(109,94,252,.18);"><div style="font-size:13px;opacity:.9;margin-bottom:6px;">You</div><div style="white-space:pre-wrap;line-height:1.55;">{text}</div></div></div>', unsafe_allow_html=True)


def chat_assistant_bubble(text: str, source_count: int = 0, mode: str = "hybrid"):
    badge = "RAG" if mode == "hybrid" else "GEN"
    st.markdown(f'<div style="display:flex;justify-content:flex-start;margin:10px 0;"><div style="max-width:82%;background:rgba(255,255,255,0.82);backdrop-filter:blur(10px);border:1px solid rgba(120,120,120,.18);padding:14px 16px;border-radius:18px 18px 18px 4px;box-shadow:0 8px 24px rgba(0,0,0,.06);"><div style="display:flex;justify-content:space-between;gap:12px;font-size:13px;opacity:.75;margin-bottom:6px;"><span>Assistant</span><span>{badge} · {source_count} sources</span></div><div style="white-space:pre-wrap;line-height:1.6;">{text}</div></div></div>', unsafe_allow_html=True)


def pick_docs_for_embedding():
    ensure_dirs()
    files = sorted([p for p in OUTPUT_DIR.glob("*.md") if p.is_file()], key=lambda x: x.name.lower())
    if not files:
        return []
    cols = st.columns(2)
    with cols[0]:
        st.markdown("### 임베딩할 자료 선택")
    with cols[1]:
        select_all = st.checkbox("전체 선택", value=True, key="embed_select_all")
    choices = [p.name for p in files]
    default = choices if select_all else choices[:min(5, len(choices))]
    return st.multiselect("대상 md 파일", choices, default=default, key="embed_doc_picker")


# ═══════════════════════════════════════════════════════════
# SPRINT 1 DISABLED — RAG Chat UI tab
# ═══════════════════════════════════════════════════════════

def render_trendy_chat_tab(embed_model: str, gen_model: str, chunk_size: int, chunk_overlap: int, top_k: int, temperature: float):
    """RAG chat tab. SPRINT 1 DISABLED."""
    # Always show the RAG tab, but feature capabilities are checked internally
    st.subheader("RAG Chat")
    st.caption("모던한 채팅 UI + RAG fallback (dual-store: ChromaDB + Qdrant)")

    init_chat_state()
    st.subheader("RAG Chat")
    st.caption("모던한 채팅 UI + RAG fallback (dual-store: ChromaDB + Qdrant)")

    if "rag_store" not in st.session_state:
        st.session_state["rag_store"] = "both"

    top_left, top_right = st.columns([4, 1])
    with top_left:
        st.markdown("""<div style="padding:14px 16px;border:1px solid rgba(120,120,120,.14);border-radius:18px;background:linear-gradient(180deg,rgba(255,255,255,.9),rgba(248,249,255,.9));"><div style="font-size:15px;font-weight:600;margin-bottom:4px;">RAG Conversation</div><div style="font-size:13px;opacity:.75;">질문을 입력하면 검색 결과를 자동으로 섞어 답변합니다.</div></div>""", unsafe_allow_html=True)
    with top_right:
        st.metric("Top K", top_k)

    store_col1, store_col2, store_col3 = st.columns(3)
    with store_col1:
        st.session_state["rag_mode"] = st.selectbox("Mode", ["hybrid", "gen_only"], index=0 if st.session_state["rag_mode"] == "hybrid" else 1)
    with store_col2:
        st.session_state["rag_store"] = st.selectbox("Vector Store", ["both", "chroma", "qdrant"], index=["both", "chroma", "qdrant"].index(st.session_state.get("rag_store", "both")), key="rag_store_picker")
    with store_col3:
        st.session_state["rag_show_context"] = st.toggle("Show context", value=st.session_state["rag_show_context"])
        if _qdrant_available():
            st.caption("Qdrant: \u2705")
        else:
            st.caption("Qdrant: \u2749 (off)")

    selected_docs = pick_docs_for_embedding()
    if selected_docs:
        st.caption(f"선택된 문서: {len(selected_docs)}개")
        st.dataframe(pd.DataFrame({"file": selected_docs}), use_container_width=True, hide_index=True)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        build_clicked = st.button("임베딩 인덱스 빌드", use_container_width=True)
    with c2:
        bench_run_clicked = st.button("벤치마크 실행", use_container_width=True)
    with c3:
        if st.button("벤치마크 기록 보기", use_container_width=True):
            bench_path = get_bench_csv(create_if_missing=True)
            if bench_path.exists():
                try:
                    df = pd.read_csv(bench_path)
                    if not df.empty or len(df.columns) > 0:
                        st.dataframe(df, use_container_width=True, hide_index=True)
                    else:
                        st.info("벤치마크 기록이 비어 있습니다. scripts/benchmark_pipeline.py 로 벤치마크를 실행하세요.")
                except Exception as e:
                    st.error(f"CSV 읽기 실패: {e}")
            else:
                st.info("벤치마크 기록이 없습니다.")
    with c4:
        st.caption(f"Collection: {COLLECTION_NAME}")

    if bench_run_clicked:
        st.info("벤치마크를 실행합니다...")
        try:
            result = subprocess.run(["python", str(Path(__file__).parent / "scripts" / "benchmark_pipeline.py"), "--glob", "data/**/*", "--limit", "10", "--output", "output/bench"], capture_output=True, text=True, timeout=600, cwd=str(PROJECT_ROOT))
            if result.returncode == 0:
                st.success("벤치마크 완료!")
                with st.expander("결과"):
                    st.text(result.stdout)
            else:
                st.error(f"벤치마크 실패:\n{result.stderr}")
        except subprocess.TimeoutExpired:
            st.error("벤치마크 시간이 초과되었습니다 (10분).")
        except Exception as e:
            st.error(f"벤치마크 실행 오류: {e}")

    if build_clicked:
        if not selected_docs:
            st.warning("임베딩할 자료를 먼저 선택하세요.")
        else:
            current_store = st.session_state.get("rag_store", "both")
            out = build_rag_store(selected_files=selected_docs, input_dir=str(OUTPUT_DIR), embed_model=embed_model, chunk_size=chunk_size, overlap=chunk_overlap, store=current_store)
            msg = f"{out['documents']} docs, {out['chunks']} chunks indexed"
            if out.get("qdrant"):
                msg += f" | Qdrant: {out['qdrant']['upserted']} upserted"
            st.success(msg)

    for msg in st.session_state["rag_chat"]:
        if msg["role"] == "user":
            chat_user_bubble(msg["content"])
        else:
            chat_assistant_bubble(msg["content"], msg.get("source_count", 0), msg.get("mode", "hybrid"))

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    prompt = st.chat_input("질문을 입력하세요… 예: 이 문서에서 핵심 요점은?")

    if prompt:
        user_text = prompt.strip()
        current_store = st.session_state.get("rag_store", "both")
        st.session_state["rag_chat"].append({"role": "user", "content": user_text})
        with st.spinner("생성 중…"):
            res = query_rag(user_text, embed_model=embed_model, gen_model=gen_model, top_k=top_k, temperature=temperature, store=current_store)
            answer = res["answer"]
            source_count = len(res.get("sources", []))
            mode = "hybrid" if res.get("contexts") else "gen_only"
            if st.session_state["rag_show_context"] and res.get("sources"):
                with st.expander("Context", expanded=False):
                    for s in res["sources"]:
                        st.markdown(f"**{s['source']} · chunk {s['chunk']}**")
                        st.code(s["snippet"], language="markdown")
        st.session_state["rag_chat"].append({"role": "assistant", "content": answer, "source_count": source_count, "mode": mode})
        st.rerun()

    if st.button("Clear", use_container_width=True):
        st.session_state["rag_chat"] = [{"role": "assistant", "content": "채팅을 초기화했습니다.", "source_count": 0, "mode": "gen_only"}]
        st.rerun()


def render_monitor_tab():
    if st.session_state.get("is_processing", False):
        st.info("청킹 처리 중입니다. 프로젝트 모니터는 잠시 후 다시 확인하세요.")
        return
    try:
        df = load_progress_df().copy()
        avg = float(df["진행률"].mean()) if not df.empty else 0.0
        todo = int((df["상태"] == "TODO").sum())
        blocked = int((df["상태"] == "BLOCKED").sum())
        done_like = int((df["진행률"] >= 60).sum())
        cache_stats = get_cache_stats()

        st.subheader("Project Monitor")
        if st.button("🔄 진행률 초기화", type="secondary", help="모든 영역의 진행률을 0%으로 초기화합니다.", use_container_width=True):
            df_reset = pd.DataFrame(DEFAULT_PROGRESS)
            df_reset.to_csv(PROGRESS_CSV, index=False)
            refresh_todo_doc(df_reset)
            if EVENTS_JSONL.exists():
                EVENTS_JSONL.write_text("")
            st.success("진행률이 초기화되었습니다.")
            st.rerun()

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("평균", f"{avg:.1f}%")
        c2.metric("60%+", f"{done_like}개")
        c3.metric("TODO", f"{todo}개")
        c4.metric("BLOCKED", f"{blocked}개")

        st.markdown("### 캐시 현황")
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("전체 개수", f"{cache_stats['count']}개")
        k2.metric("전체 용량", f"{cache_stats['mb']} MB")
        k3.metric("MD 개수", f"{cache_stats['md_count']}개")
        k4.metric("Chunks 개수", f"{cache_stats['chunk_count']}개")
        st.progress(min(cache_stats["bytes"] / (50 * 1024 * 1024), 1.0), text=f"추정 캐시 {cache_stats['mb']} MB")
        c1, c2, c3 = st.columns(3)
        c1.metric("MD 용량", f"{round(cache_stats['md_bytes'] / (1024 * 1024), 2)} MB")
        c2.metric("Chunks 용량", f"{round(cache_stats['chunk_bytes'] / (1024 * 1024), 2)} MB")
        c3.metric("기타 용량", f"{round(cache_stats['other_bytes'] / (1024 * 1024), 2)} MB")
        if cache_stats["items"]:
            st.dataframe(pd.DataFrame(cache_stats["items"]), use_container_width=True, hide_index=True)
        else:
            st.info("캐시 항목이 없습니다.")
    except Exception as e:
        safe_log_exception(f"render_monitor_tab failed: {e}")


def render_processing_tab(use_ocr: bool, chunk_size: int, chunk_overlap: int):
    if st.session_state.get("is_processing", False):
        st.info("이미 처리 중입니다.")
        return
    try:
        file_list = scan_directory(str(RAW_DIR))
        st.subheader("Processing")
        if not file_list:
            st.warning("지원 형식 파일이 없습니다.")
            return

        selected = st.multiselect("처리할 파일", [f["name"] for f in file_list], default=[f["name"] for f in file_list[: min(5, len(file_list))]])

        c1, c2 = st.columns(2)
        with c1:
            start_parse = st.button("Parse 시작", use_container_width=True)
        with c2:
            clear_after = st.checkbox("처리 후 재실행", value=False)

        status_box = st.empty()
        progress_box = st.progress(0, text="대기 중")
        live_box = st.empty()
        results_box = st.empty()

        if start_parse:
            st.session_state["is_processing"] = True
            try:
                results = []
                total = max(1, len(selected))
                converter = build_converter(use_ocr)
                splitter = build_splitter(chunk_size, chunk_overlap)
                file_map = {f["name"]: f for f in file_list}

                for idx, name in enumerate(selected, start=1):
                    file_info = file_map.get(name)
                    if not file_info:
                        status_box.warning(f"파일 없음: {name}")
                        continue
                    status_box.info(f"처리 중: {name}")
                    st.session_state["current_file"] = name
                    st.session_state["current_stage"] = "start"

                    def report(stage, message, progress=None):
                        st.session_state["current_stage"] = stage
                        if progress is not None:
                            live_box.write(f"현재 파일: {name} | 단계: {stage} | {message}")

                    result = process_one_file(file_info={**file_info, "use_ocr": use_ocr}, converter=converter, splitter=splitter, output_dir=str(OUTPUT_DIR), chunk_size=chunk_size, chunk_overlap=chunk_overlap, report=report)

                    success, logs = result["success"], result["logs"]
                    results.append({"file": name, "success": success, "log_count": len(logs), "chunks": result.get("metrics", {}).get("chunk_count"), "language": result.get("metrics", {}).get("language")})

                    with st.expander(f"로그: {name}", expanded=not success):
                        for item in logs:
                            cls, msg = item.get("cls", "log-info"), item.get("msg", "")
                            if cls == "log-ok":
                                st.success(msg)
                            elif cls == "log-warn":
                                st.warning(msg)
                            else:
                                st.write(msg)
                        if success and result.get("artifacts", {}).get("opt_md_path"):
                            st.caption(f"최적화 MD: {result['artifacts']['opt_md_path']}")

                    if success:
                        append_event("parse_completed", note=name)
                        append_event("clean_completed", note=name)
                        append_event("chunk_completed", note=name)

                    progress_box.progress(idx / total, text=f"{idx}/{total} 처리 완료")
                    live_box.write(f"현재 파일: {st.session_state.get('current_file', '-')} | 단계: {st.session_state.get('current_stage', '-')}")
                    time.sleep(0.05)

                if results:
                    ok_count = sum(1 for r in results if r["success"])
                    st.success(f"{ok_count}/{len(results)}개 처리 완료")
                    results_box.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)

                    # Display output file paths prominently (SPRINT 2: make output location visible)
                    if ok_count > 0:
                        st.markdown("**Output files:**")
                        for r in results:
                            if r["success"]:
                                md_stem = r.get("file", "")
                                # Canonical MD is named {stem}_md.md where stem = source_name with dots replaced by underscore
                                stem_safe = md_stem.replace(".", "_")
                                canonical_md = f"output/{stem_safe}_md.md"
                                st.caption(f"  ✓ `{canonical_md}` (canonical markdown)")

            finally:
                st.session_state["is_processing"] = False
                progress_box.progress(1.0, text="처리 완료")

    except Exception as e:
        safe_log_exception(f"render_processing_tab failed: {e}")


def render_analysis_tab():
    if st.session_state.get("is_processing", False):
        st.info("청킹 처리 중입니다. 분석 탭은 잠시 후 다시 확인하세요.")
        return

    st.subheader("Analysis")
    md_files = sorted([p for p in OUTPUT_DIR.glob("*.md") if "_chunks_" not in p.stem], key=lambda p: p.name.lower())
    if not md_files:
        st.info("분석할 md 파일이 없습니다.")
        return

    choice = st.selectbox("md 파일 선택", [p.name for p in md_files])
    target = OUTPUT_DIR / choice
    raw_text = target.read_text(encoding="utf-8", errors="ignore")
    meta, body = _parse_frontmatter(raw_text)
    chunk_path = OUTPUT_DIR / f"{target.stem}_chunks.txt"
    chunks_text = chunk_path.read_text(encoding="utf-8", errors="ignore") if chunk_path.exists() else ""
    key = f"analysis_text_{target.name}"

    if key not in st.session_state or st.session_state.get("analysis_loaded_file") != target.name:
        st.session_state[key] = body
        st.session_state["analysis_loaded_file"] = target.name

    file_type = meta.get("source_type", "md") or (target.suffix.lstrip(".") if target.suffix else "md")
    is_ocr = meta.get("noise_mode", "") == "pdf_ocr"
    valid_text_types = {"txt", "md", "docx", "epub", "html", "htm", "rtf", "pdf"}
    if not file_type or file_type.lower() not in valid_text_types:
        file_type = target.suffix.lstrip(".").lower() or "md"

    noise = _noise_for_display(calculate_noise_score(body, file_type=file_type, is_ocr=is_ocr))
    c1, c2 = st.columns([1, 2])

    with c1:
        render_noise_bar(noise["score"], noise["usable"], noise["level"])
        st.metric("noise", f"{noise['score']:.1f}/100")
        st.metric("사용 가능", "YES" if noise["usable"] else "NO")
        st.metric("구간", noise["level"])
        st.metric("언어", meta.get("language", "-"))
        st.caption(f"reason: {noise['reason']}")
        if st.button("복사", use_container_width=True):
            st.code(st.session_state.get(key, ""), language="markdown")
        if st.button("수정본 저장", use_container_width=True):
            if meta:
                frontmatter = "\n".join(f"{k}: {v}" for k, v in meta.items())
                saved = f"---\n{frontmatter}\n---\n\n{st.session_state.get(key, body)}"
            else:
                saved = st.session_state.get(key, body)
            target.write_text(saved, encoding="utf-8")
            st.success("저장됨")
            st.rerun()

    with c2:
        tab_a, tab_b = st.tabs(["md 본문", "chunks"])
        with tab_a:
            st.text_area("내용", key=key, height=520)
        with tab_b:
            st.text_area("chunks", value=chunks_text, height=520, key=f"chunks_{target.name}")


def main():
    ensure_dirs()
    for k, v in [("pending_rerun", False), ("is_processing", False)]:
        if k not in st.session_state:
            st.session_state[k] = v
    if feature_enabled("embedding"):
        for k, v in [("embed_model", DEFAULT_EMBED_MODEL), ("gen_model", DEFAULT_GEN_MODEL)]:
            if k not in st.session_state:
                st.session_state[k] = v
    if "chunk_size" not in st.session_state:
        st.session_state["chunk_size"] = DEFAULT_CHUNK_SIZE
    if "chunk_overlap" not in st.session_state:
        st.session_state["chunk_overlap"] = DEFAULT_CHUNK_OVERLAP
    if "top_k" not in st.session_state:
        st.session_state["top_k"] = RAG_TOP_K
    if "temperature" not in st.session_state:
        st.session_state["temperature"] = DEFAULT_TEMPERATURE

    st.title(f"{APP_NAME} v{APP_VERSION}")
    st.caption("Document parsing / cleaning / chunking / monitoring / RAG / trendy chat")

    with st.sidebar:
        st.header("Settings")
        use_ocr = st.checkbox("Use OCR", value=False)

    # [SPRINT1] Embedding/LLM model options — Sprint 1 shows placeholder
    if feature_enabled("embedding"):
        dynamic_models = list_ollama_models()
        embed_choices = dynamic_models or EMBED_MODEL_OPTIONS
        gen_choices = dynamic_models or GEN_MODEL_OPTIONS
        if st.session_state["embed_model"] not in embed_choices:
            st.session_state["embed_model"] = embed_choices[0]
        if st.session_state["gen_model"] not in gen_choices:
            st.session_state["gen_model"] = gen_choices[0]
        st.session_state["embed_model"] = st.selectbox("Embedding model", embed_choices, index=embed_choices.index(st.session_state["embed_model"]))
        st.session_state["gen_model"] = st.selectbox("LLM model", gen_choices, index=gen_choices.index(st.session_state["gen_model"]))
    else:
        st.info("[Sprint 1] Embedding/LLM settings disabled — will be enabled in Sprint 2")
        st.session_state["embed_model"] = "n/a"
        st.session_state["gen_model"] = "n/a"

        st.session_state["chunk_size"] = st.number_input("Chunk Size", value=int(st.session_state["chunk_size"]), min_value=100, step=100)
        st.session_state["chunk_overlap"] = st.number_input("Chunk Overlap", value=int(st.session_state["chunk_overlap"]), min_value=0, step=10)

        if feature_enabled("rag"):
            st.session_state["top_k"] = st.slider("Top K", min_value=1, max_value=10, value=int(st.session_state["top_k"]))
            st.session_state["temperature"] = st.slider("Temperature", min_value=0.0, max_value=1.5, value=float(st.session_state["temperature"]), step=0.05)
            st.caption(f"Collection: {COLLECTION_NAME}")

        if st.button("Cache Clear"):
            cleanup_cache()
            st.success("Cache cleared")
            st.rerun()

    tab1, tab2, tab3, tab4 = st.tabs(["Parse", "Analyze", "Project", "RAG"])
    with tab1:
        render_processing_tab(use_ocr=use_ocr, chunk_size=int(st.session_state["chunk_size"]), chunk_overlap=int(st.session_state["chunk_overlap"]))
    with tab2:
        render_analysis_tab()
    with tab3:
        render_monitor_tab()
    with tab4:
        # Always show RAG tab - feature checking moved to individual components
        render_trendy_chat_tab(embed_model=st.session_state["embed_model"], gen_model=st.session_state["gen_model"], chunk_size=int(st.session_state["chunk_size"]), chunk_overlap=int(st.session_state["chunk_overlap"]), top_k=int(st.session_state["top_k"]), temperature=float(st.session_state["temperature"]))


if __name__ == "__main__":
    main()