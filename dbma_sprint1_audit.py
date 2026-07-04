"""
dbma_sprint1_audit.py — Sprint 1 Violation Audit for dbma.py

This file is ADDITIVE ONLY. No lines deleted from dbma.py.
All remediation uses conditional wrapping with SPRINT1_ONLY flag.

Usage:
  Copy the flag section to top of dbma.py after imports
  Then apply each标记 below to wrap violating sections

SPRINT 1 BOUNDARY (strict):
  ✅ ALLOWED: parse → clean → chunk → store {stem}.md
  ❌ PROHIBITED: embedding, vector DB, LLM generation, retrieval
"""

# ═══════════════════════════════════════════════════════════
# APPLY TO dbma.py — ADD AFTER IMPORTS (around line 25)
# ═══════════════════════════════════════════════════════════

"""
SPRINT1_ONLY = True  # Set False to enable all features (Sprint 2+)

If SPRINT1_ONLY is True, the following are DISABLED:
  - All embedding calls (Ollama + sentence_transformers)
  - All ChromaDB operations
  - All Qdrant operations  
  - All Ollama LLM generation
  - All retrieval/query logic
"""

# ═══════════════════════════════════════════════════════════
# VIOLATION AUDIT — Exact Lines in dbma.py
# ═══════════════════════════════════════════════════════════

VIOLATIONS = {
    # ── CATEGORY 1: PROHIBITED IMPORTS (lines 10-11) ──
    "violation_01_import_chromadb": {
        "file": "dbma.py",
        "line": 10,
        "code": "import chromadb",
        "category": "vector_db",
        "severity": "HIGH",
        "wrap": """
if not SPRINT1_ONLY:
    import chromadb
""",
    },
    "violation_02_import_ollama": {
        "file": "dbma.py",
        "line": 11,
        "code": "import ollama",
        "category": "llm",
        "severity": "HIGH",
        "wrap": """
if not SPRINT1_ONLY:
    import ollama
""",
    },

    # ── CATEGORY 2: EMBEDDING IMPORT (line 28) ──
    "violation_03_import_embedder": {
        "file": "dbma.py",
        "line": 28,
        "code": "from core.embedder import embed as embed_via_transformer",
        "category": "embedding",
        "severity": "HIGH",
        "wrap": """
if not SPRINT1_ONLY:
    from core.embedder import embed as embed_via_transformer
""",
    },

    # ── CATEGORY 3: QDRANT IMPORTS (lines 36-38) ──
    "violation_04_import_qdrant_related": {
        "file": "dbma.py",
        "line": 36,
        "code": """from core.ingest import insert as ingest_to_qdrant
from core.qdrant_init import init_collection as qdrant_init_collection
from core.search import search as search_qdrant_index""",
        "category": "vector_db",
        "severity": "HIGH",
        "wrap": """
if not SPRINT1_ONLY:
    from core.ingest import insert as ingest_to_qdrant
    from core.qdrant_init import init_collection as qdrant_init_collection
    from core.search import search as search_qdrant_index
""",
    },

    # ── CATEGORY 4: EMBEDDING FUNCTION (lines 157-181) ──
    "violation_05_embed_text_ollama": {
        "file": "dbma.py",
        "line_start": 157,
        "line_end": 181,
        "code": "def embed_text_ollama(texts, model: str = DEFAULT_EMBED_MODEL) -> list:",
        "category": "embedding",
        "severity": "HIGH",
        "wrap": """
# ═══ Sprint 1 DISABLED ═══
if not SPRINT1_ONLY:
def embed_text_ollama(texts, model: str = DEFAULT_EMBED_MODEL) -> list:
    ...
# ═══ END disabled ═══
""",
    },

    # ── CATEGORY 5: QDRANT HELPER FUNCTIONS (lines 386-409) ──
    "violation_06_qdrant_helpers": {
        "file": "dbma.py",
        "line_start": 386,
        "line_end": 409,
        "code": """def _qdrant_available() -> bool:
def _embed_text_qdrant(texts: list[str], model: str = DEFAULT_EMBED_MODEL) -> list[list[float]]:""",
        "category": "vector_db",
        "severity": "HIGH",
        "wrap": """
# ═══ Sprint 1 DISABLED ═══
if not SPRINT1_ONLY:
def _qdrant_available() -> bool:
    ...

def _embed_text_qdrant(texts: list[str], model: str = DEFAULT_EMBED_MODEL) -> list[list[float]]:
    ...
# ═══ END disabled ═══
""",
    },

    # ── CATEGORY 6: QDRANT UPSERT FUNCTION (lines 412-468) ──
    "violation_07_upsert_to_qdrant": {
        "file": "dbma.py",
        "line_start": 412,
        "line_end": 468,
        "code": "def upsert_to_qdrant(...):",
        "category": "vector_db",
        "severity": "HIGH",
        "wrap": """
# ═══ Sprint 1 DISABLED ═══
if not SPRINT1_ONLY:
def upsert_to_qdrant(...):
    ...
# ═══ END disabled ═══
""",
    },

    # ── CATEGORY 7: QDRANT QUERY FUNCTION (lines 471-509) ──
    "violation_08_query_qdrant": {
        "file": "dbma.py",
        "line_start": 471,
        "line_end": 509,
        "code": "def query_qdrant(...):",
        "category": "vector_db",
        "severity": "HIGH",
        "wrap": """
# ═══ Sprint 1 DISABLED ═══
if not SPRINT1_ONLY:
def query_qdrant(...):
    ...
# ═══ END disabled ═══
""",
    },

    # ── CATEGORY 8: DUAL BACKEND EMBEDDING (lines 512-552) ──
    "violation_09_embed_texts": {
        "file": "dbma.py",
        "line_start": 512,
        "line_end": 552,
        "code": "def _embed_texts(texts: List[str], model: str = DEFAULT_EMBED_MODEL) -> List[List[float]]:",
        "category": "embedding",
        "severity": "HIGH",
        "wrap": """
# ═══ Sprint 1 DISABLED ═══
if not SPRINT1_ONLY:
def _embed_texts(texts: List[str], model: str = DEFAULT_EMBED_MODEL) -> List[List[float]]:
    ...
# ═══ END disabled ═══
""",
    },

    # ── CATEGORY 9: RAG STORE BUILDER (lines 559-625) ──
    "violation_10_build_rag_store": {
        "file": "dbma.py",
        "line_start": 559,
        "line_end": 625,
        "code": "def build_rag_store(...):",
        "category": "vector_db + embedding",
        "severity": "HIGH",
        "description": "Builds embeddings for BOTH ChromaDB and Qdrant",
        "wrap": """
# ═══ Sprint 1 DISABLED ═══
if not SPRINT1_ONLY:
def build_rag_store(...):
    ...
# ═══ END disabled ═══
""",
    },

    # ── CATEGORY 10: RAG QUERY FUNCTION (lines 628-758) ──
    "violation_11_query_rag": {
        "file": "dbma.py",
        "line_start": 628,
        "line_end": 758,
        "code": "def query_rag(...):",
        "category": "retrieval + embedding + LLM",
        "severity": "HIGH",
        "description": "Full RAG pipeline: embedding → ChromaDB/Qdrant query → Ollama generation",
        "wrap": """
# ═══ Sprint 1 DISABLED ═══
if not SPRINT1_ONLY:
def query_rag(...):
    ...
# ═══ END disabled ═══
""",
    },

    # ── CATEGORY 11: OLLAMA GENERATION (line 732) ──
    "violation_12_ollama_generate": {
        "file": "dbma.py",
        "line": 732,
        "code": 'answer = ollama.generate(model=gen_model, prompt=prompt, options={"temperature": temperature})["response"]',
        "category": "llm",
        "severity": "HIGH",
        "wrap": """
# ═══ Sprint 1 DISABLED ═══
if not SPRINT1_ONLY:
    answer = ollama.generate(model=gen_model, prompt=prompt, options={"temperature": temperature})["response"]
else:
    answer = "[Sprint 1: LLM generation disabled] Please set SPRINT1_ONLY=False to enable."
# ═══ END disabled ═══
""",
    },

    # ── CATEGORY 12: CHROMADB CLIENT (lines 328-334) ──
    "violation_13_vector_client": {
        "file": "dbma.py",
        "line_start": 328,
        "line_end": 334,
        "code": """def get_vector_client():
    return chromadb.PersistentClient(path=str(CHROMA_DIR))

def get_collection():
    client = get_vector_client()
    return client.get_or_create_collection(name=COLLECTION_NAME)""",
        "category": "vector_db",
        "severity": "HIGH",
        "wrap": """
# ═══ Sprint 1 DISABLED ═══
if not SPRINT1_ONLY:
def get_vector_client():
    return chromadb.PersistentClient(path=str(CHROMA_DIR))

def get_collection():
    client = get_vector_client()
    return client.get_or_create_collection(name=COLLECTION_NAME)
# ═══ END disabled ═══
""",
    },

    # ── CATEGORY 13: RAG CHUNK TEXT (line 337) — LOW SEVERITY ──
    "viuation_14_rag_chunk_text": {
        "file": "dbma.py",
        "line": 337,
        "code": "def rag_chunk_text(text: str, chunk_size: int = DEFAULT_CHUNK_SIZE, overlap: int = DEFAULT_CHUNK_OVERLAP) -> List[str]:",
        "category": "embedding (indirect)",
        "severity": "MEDIUM",
        "description": "Used by build_rag_store for pre-embedding chunking — may be kept if needed standalone",
        "wrap": """
# ═══ Sprint 1 DISABLED (wrapped) ═══
if not SPRINT1_ONLY:
def rag_chunk_text(text: str, chunk_size: int = DEFAULT_CHUNK_SIZE, overlap: int = DEFAULT_CHUNK_OVERLAP) -> List[str]:
    ...
# ═══ END disabled ═══
""",
    },

    # ── CATEGORY 14: READ INDEXABLE DOCS (lines 342-362) — MEDIUM SEVERITY ──
    "violation_15_read_indexable_docs": {
        "file": "dbma.py",
        "line_start": 342,
        "line_end": 362,
        "code": "def read_indexable_docs(...):",
        "category": "embedding (indirect)",
        "severity": "MEDIUM",
        "description": "Prepares docs for embedding — kept if chunking needs doc discovery",
        "wrap": """
# ═══ Sprint 1: KEEP (needed for chunking) OR disable if unused ───
if not SPRINT1_ONLY or USE_DOC_DISCOVERY:
def read_indexable_docs(...):
    ...
""",
    },

    # ── CATEGORY 15: OLLAMA MODELS LIST (lines 365-373) — LOW SEVERITY ──
    "violation_16_list_ollama_models": {
        "file": "dbma.py",
        "line_start": 365,
        "line_end": 379,
        "code": """def list_ollama_models() -> List[str]:
def _model_supports_embeddings(model: str) -> bool:""",
        "category": "llm (UI helper)",
        "severity": "LOW",
        "description": "Only needed for UI model picker — can wrap or leave as dead code",
        "wrap": """
# ═══ Sprint 1 DISABLED (UI only) ═══
if not SPRINT1_ONLY:
def list_ollama_models() -> List[str]:
    ...

def _model_supports_embeddings(model: str) -> bool:
    ...
# ═══ END disabled ═══
""",
    },

    # ── CATEGORY 16: BENCHMARK ROW (lines 761-784) — LOW SEVERITY ──
    "violation_17_append_benchmark_row": {
        "file": "dbma.py",
        "line_start": 761,
        "line_end": 784,
        "code": "def append_benchmark_row(embed_model, gen_model, chunk_size, ...):",
        "category": "RAG benchmark (metadata only)",
        "severity": "LOW",
        "description": "Records RAG params to CSV — can be kept for Sprint 2 benchmarks",
        "wrap": """
# ═══ Sprint 1: KEEP or disable at discretion ───
if not SPRINT1_ONLY:
def append_benchmark_row(...):
    ...
""",
    },

    # ── CATEGORY 17: RENDER TALKY CHAT TAB (lines 864-1016) — HIGH SEVERITY ──
    "violation_18_render_trendy_chat_tab": {
        "file": "dbma.py",
        "line_start": 864,
        "line_end": 1016,
        "code": "def render_trendy_chat_tab(...):",
        "category": "retrieval + UI",
        "severity": "HIGH",
        "description": "Full RAG chat UI tab — calls build_rag_store() and query_rag()",
        "wrap": """
# ═══ Sprint 1 DISABLED ═══
if not SPRINT1_ONLY:
def render_trendy_chat_tab(embed_model, gen_model, chunk_size, ...):
    ...
else:
def render_trendy_chat_tab(...):
    st.subheader("RAG Chat")
    st.info("[Sprint 1: RAG disabled — will be enabled in Sprint 2]")
# ═══ END disabled ═══
""",
    },

    # ── CATEGORY 18: MODEL SUPPORTS EMBEDDINGS CHECK (line 958) ──
    "violation_19_model_supports_embeddings_check": {
        "file": "dbma.py",
        "line": 958,
        "code": "if not _model_supports_embeddings(embed_model): st.warning(...)",
        "category": "embedding (UI warning)",
        "severity": "LOW",
        "wrap": """
# ═══ Sprint 1 DISABLED ═══
if not SPRINT1_ONLY:
    if not _model_supports_embeddings(embed_model):
        st.warning("...")
# ═══ END disabled ═══
""",
    },
}

# ═══════════════════════════════════════════════════════════
# SUMMARY OF VIOLATIONS
# ═══════════════════════════════════════════════════════════

SUMMARY = """
┌─────────────────────────────────────────────────────────┐
│           SPRINT 1 VIOLATION AUDIT SUMMARY               │
├─────────────────────────────────────────────────────────┤
│ Total violations found: {count}                          │
│                                                         │
│ By Category:                                            │
│   embedding:    {embedding_count} items                 │
│   vector_db:    {vector_db_count} items                 │
│   llm:          {llm_count} items                       │
│   retrieval:    {retrieval_count} items                 │
│                                                         │
│ By Severity:                                            │
│   HIGH:   {high_count} — must disable for Sprint 1     │
│   MEDIUM: {med_count} — review for necessity            │
│   LOW:    {low_count} — UI helpers, can keep disabled   │
│                                                         │
│ Files to modify (ALL ADDITIVE):                         │
│   dbma.py → wrap each section with "if not SPRINT1_ONLY"│
│                                                         │
│ Flag definition (add after imports in dbma.py):         │
│   SPRINT1_ONLY = True  # Set False for Sprint 2+       │
└─────────────────────────────────────────────────────────┘
""".format(
    count=len(VIOLATIONS),
    embedding_count=sum(1 for v in VIOLATIONS.values() if "embedding" in v["category"]),
    vector_db_count=sum(1 for v in VIOLATIONS.values() if "vector_db" in v["category"]),
    llm_count=sum(1 for v in VIOLATIONS.values() if v["category"] == "llm"),
    retrieval_count=sum(1 for v in VIOLATIONS.values() if "retrieval" in v["category"]),
    high_count=sum(1 for v in VIOLATIONS.values() if v["severity"] == "HIGH"),
    med_count=sum(1 for v in VIOLATIONS.values() if v["severity"] == "MEDIUM"),
    low_count=sum(1 for v in VIOLATIONS.values() if v["severity"] == "LOW"),
)

if __name__ == "__main__":
    print(SUMMARY)
    print("\nVIOLATION DETAILS:")
    for key, v in sorted(VIOLATIONS.items()):
        print(f"\n  [{key}]")
        print(f"    File: {v['file']}:{v.get('line_start', v.get('line', 'N/A'))}")
        print(f"    Category: {v['category']}")
        print(f"    Severity: {v['severity']}")
        print(f"    Code: {v['code'][:80]}...")