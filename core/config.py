"""
core/config.py — 단일 설정 소스 (Source of Truth)

config.yaml에서 설정을 읽으며, 하위 호환성을 위해 기본값도 제공한다.
"""

import os
import warnings
from pathlib import Path
from typing import Any

# config.yaml 로드 (PyYAML 필수 — 누락 시 config.yaml이 조용히 무시되고
# DEFAULT_OUTPUT_DIR 등이 하드코딩 fallback으로 빠지는 silent corruption을
# 막기 위해 즉시 실패한다. SPRINT20-E2에서 이 silent fallback이 실제로
# TSU dataset을 손상시킬 뻔한 사고로 이어진 바 있다.)
_CFG_RAW: dict[str, Any] | None = None  # pyright: ignore[reportAny]
CFG: dict[str, Any] = {}  # pyright: ignore[reportAny]
try:
    import yaml
except ImportError as exc:
    raise RuntimeError(
        "PyYAML is required for DBMA configuration loading. "
        "Install dependencies from requirements.txt."
    ) from exc

_config_path = Path(__file__).parent.parent / "config.yaml"
if _config_path.exists():
    with open(_config_path, "r", encoding="utf-8") as f:
        _loaded = yaml.safe_load(f)
        if isinstance(_loaded, dict):
            CFG.update(_loaded)

# ── 앱 메타 ──────────────────────────────────────────────
_yaml_app = CFG.get("app", {})
APP_VERSION = _yaml_app.get("version", "0.6.4")
APP_NAME = _yaml_app.get("name", "DBMAr")

warnings.filterwarnings("ignore", category=UserWarning)
# [SPRINT20-G3] Previously forced the root logger to ERROR here, which
# silently suppressed WARNING/INFO logs project-wide the moment core.config
# was imported (e.g. core/extractors.py's optional-dependency warnings never
# reached anyone). Application logging level is the entry point's
# responsibility, not a config-loading side effect — removed.

# ── 디렉토리 (하위 호환성 기본값) ───────────────────────
CORE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(CORE_DIR)

_yaml_dirs = CFG.get("directories", {})
DATA_DIR = os.path.join(BASE_DIR, "data")
_yaml_raw_dir = _yaml_dirs.get("raw_dir", "data/raw")
DEFAULT_OUTPUT_DIR = _yaml_dirs.get("output_dir", "output")

# 처리 파일 저장 폴더 일원화: config.yaml 기준 (폴더 존재 여부와 무관)
if not os.path.exists(_yaml_raw_dir):
    _yaml_raw_dir = os.path.join(DATA_DIR, "RAW")
DEFAULT_RAW_DIR = _yaml_raw_dir  # type: ignore[assignment]  # resolved after condition check

# [SPRINT17-Phase5-M1b-0.1] TSU/bench path configuration authority — additive
# only, not yet referenced by core/retrieval.py or scripts/ (see M1b-0.2+).
DEFAULT_BENCH_DIR = _yaml_dirs.get("bench_dir", "output/bench")
DEFAULT_TSU_DATASET_PATH = os.path.join(DEFAULT_BENCH_DIR, "tsu_dataset.jsonl")
DEFAULT_TSU_MANIFEST_PATH = os.path.join(DEFAULT_BENCH_DIR, "tsu_manifest.json")


# [SPRINT20-I-C-2-B2] Registry Path Authority — single source for the
# {output_dir}/registry/documents.json path, previously reconstructed in 7
# sites (CUE-20I-C-1.5). registry_path_for() serves callers with a variable
# output_dir; DEFAULT_REGISTRY_PATH is the default (output_dir omitted).
def registry_path_for(output_dir: str) -> str:
    return os.path.join(output_dir, "registry", "documents.json")


DEFAULT_REGISTRY_PATH = registry_path_for(DEFAULT_OUTPUT_DIR)

# ── 확장자 ───────────────────────────────────────────────
SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".txt",
    ".md",
    ".docx",
    ".epub",
    ".html",
    ".htm",
    ".rtf",
}

# ── 청킹 기본값 ──────────────────────────────────────────
_yaml_chunking = CFG.get("chunking", {})
DEFAULT_CHUNK_SIZE = _yaml_chunking.get("default_size", 1200)
DEFAULT_CHUNK_OVERLAP = _yaml_chunking.get("default_overlap", 120)
# [SPRINT29-B] Single source for the minimum chunk length. Previously the
# value 80 was hardcoded independently in core/chunking_optimizer.py and
# core/processing.py, while config.yaml declared an unrelated (and
# never-loaded) min_chunk_size: 200. Loaded here so both call sites read
# one value; default 80 preserves the pre-SPRINT29-B chunking behavior.
DEFAULT_MIN_CHUNK_SIZE = _yaml_chunking.get("min_chunk_size", 80)
# [SPRINT29-B] Advisory only — the chunker does not enforce a hard maximum;
# the effective upper bound is a soft cap of chunk_size * 1.5 in
# core/chunking_optimizer.py (_split_by_paragraphs). Loaded for provenance/
# tooling visibility, not consumed by the splitting logic.
DEFAULT_MAX_CHUNK_SIZE = _yaml_chunking.get("max_chunk_size", 5000)

# ── 벡터DB 설정 (하위 호환성) ───────────────────────────
_yaml_vdb = CFG.get("vector_db", {})
VECTOR_DB_PRIMARY = _yaml_vdb.get("primary", "chroma")
CHROMA_COLLECTION = _yaml_vdb.get("chroma", {}).get("collection_name", "dbmar_docs")
CHROMA_PERSIST_DIR = _yaml_vdb.get("chroma", {}).get("persist_directory", "chroma_db")
QDRANT_URL = _yaml_vdb.get("qdrant", {}).get("url", "http://localhost:6333")

# ── 임베딩 모델 ──────────────────────────────────────────
_yaml_emb = CFG.get("embedding", {})
EMBEDDING_MODEL = _yaml_emb.get("model", "bge-m3:latest")  # Default to bge-m3 for consistency
EMBEDDING_DIMENSION = 1024  # Enforce single embedding dimension policy - all embeddings must be 1024-dimensional
# This ensures compatibility with BGE-M3 models and prevents dimension mismatch errors
# Override any configuration that specifies different dimensions

# ── Ollama 모델 (dbma.py UI용) ──────────────────────────
_yaml_ollama = CFG.get("ollama", {})
DEFAULT_EMBED_MODEL = _yaml_ollama.get("default_embed_model", "bge-m3:latest")
DEFAULT_GEN_MODEL = _yaml_ollama.get("default_gen_model", "my-theology-bot:latest")
EMBED_MODEL_OPTIONS = _yaml_ollama.get("embed_model_options", ["bge-m3:latest", "nomic-embed-text", "mxbai-embed-large"])
GEN_MODEL_OPTIONS = _yaml_ollama.get("gen_model_options", ["my-theology-bot:latest", "llama3.1:8b", "llama3:latest"])

# ── 진행률 기본값 ─────────────────────────────────────────
_yaml_progress = CFG.get("progress_defaults", [])
DEFAULT_PROGRESS = [
    {"영역": p["area"], "진행률": p["progress"], "상태": p["status"]}
    for p in _yaml_progress
] if _yaml_progress else [
    {"영역": "멀티 포맷 추출", "진행률": 75, "상태": "DOING"},
    {"영역": "텍스트 정제", "진행률": 60, "상태": "DOING"},
    {"영역": "청킹 전략", "진행률": 45, "상태": "DOING"},
    {"영역": "임베딩/인덱싱", "진행률": 50, "상태": "DOING"},
    {"영역": "평가 루프", "진행률": 35, "상태": "DOING"},
    {"영역": "로그/추적성", "진행률": 30, "상태": "TODO"},
    {"영역": "UI/탭 구조", "진행률": 25, "상태": "TODO"},
    {"영역": "문서화/운영", "진행률": 65, "상태": "DOING"},
]

# ── RAG 설정 ─────────────────────────────────────────────
_yaml_rag = CFG.get("rag", {})
RAG_MIN_LEN = _yaml_rag.get("min_length", 80)
RAG_MAX_NOISE = _yaml_rag.get("max_noise", 70.0)
RAG_TOP_K = _yaml_rag.get("top_k", 4)
# [SPRINT20-I-E] 문서 다양성: top-k 내 동일 document_id 최대 노출 수.
# 0이면 비활성(기존 동작). 특정 문서(예: 과청킹된 2 Kings Vol13)가 top-k를
# 독점하는 편중을 완화한다.
RETRIEVAL_DOCUMENT_CAP = _yaml_rag.get("document_cap", 2)
DEFAULT_TEMPERATURE = _yaml_rag.get("default_temperature", 0.2)
RAG_CHUNK_SIZE = _yaml_rag.get("chunk_size", 1200)
RAG_CHUNK_OVERLAP = _yaml_rag.get("chunk_overlap", 120)

# ── UI 기본값 ───────────────────────────────────────────
_yaml_ui = CFG.get("ui", {})
UI_CHUNK_SIZE = _yaml_ui.get("chunk_size", 1200)
UI_CHUNK_OVERLAP = _yaml_ui.get("chunk_overlap", 120)
UI_USE_OCR = _yaml_ui.get("use_ocr", False)

# ── Sprint 1 출력 형식 ──────────────────────────────────
_yaml_output = CFG.get("output", {})
OUTPUT_FORMAT_MD_ONLY = _yaml_output.get("md_only", True)  # True = .md만 생성 (기본값)
