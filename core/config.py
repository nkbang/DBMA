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
APP_VERSION = _yaml_app.get("version", "1.3.0")
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

# [DBMA-SEARCH-INFRA-001 Phase2-4] core/candidate_generator.py's Tantivy
# index directory — kept alongside the TSU dataset it mirrors.
DEFAULT_CANDIDATE_INDEX_DIR = os.path.join(DEFAULT_BENCH_DIR, "tantivy_index")

# [DBMA-SEARCH-INFRA-001 Phase2-3] core/bible_index.py's canonical-key ->
# tsu_id posting-list database — independent of the vector/BM25 indexes.
DEFAULT_BIBLE_INDEX_PATH = os.path.join(DEFAULT_BENCH_DIR, "bible_index.sqlite3")

# [DBMA-SEARCH-INFRA-001 HQ 제안 ⑨] core/search_telemetry.py's per-query
# telemetry database.
DEFAULT_SEARCH_TELEMETRY_PATH = os.path.join(DEFAULT_BENCH_DIR, "search_telemetry.sqlite3")

# [DBMA-SEARCH-INFRA-001 HQ 제안 ⑥] core/search_cache.py's L2 (SQLite) tier.
DEFAULT_SEARCH_CACHE_PATH = os.path.join(DEFAULT_BENCH_DIR, "search_cache.sqlite3")


# [SPRINT20-I-C-2-B2] Registry Path Authority — single source for the
# {output_dir}/registry/documents.json path, previously reconstructed in 7
# sites (CUE-20I-C-1.5). registry_path_for() serves callers with a variable
# output_dir; DEFAULT_REGISTRY_PATH is the default (output_dir omitted).
def registry_path_for(output_dir: str) -> str:
    return os.path.join(output_dir, "registry", "documents.json")


DEFAULT_REGISTRY_PATH = registry_path_for(DEFAULT_OUTPUT_DIR)

# [DBMA-UX-003] Sample Library — a small side-list of document_ids that are
# curated read-only examples (Design Brief §2.5). Deliberately kept OUT of
# identity_registry.py's schema (documents.json) rather than adding an
# is_sample field there — this is a UI-only concern, and touching the core
# registry contract for it would be unnecessary Core architecture surface
# for what's fundamentally a display/permission flag. ui/pages/library.py
# reads this file to decide which registry entries render as "기본 자료
# (읽기 전용)".
def sample_library_path_for(output_dir: str) -> str:
    return os.path.join(output_dir, "registry", "sample_library.json")


DEFAULT_SAMPLE_LIBRARY_PATH = sample_library_path_for(DEFAULT_OUTPUT_DIR)

# [docs/LOCAL_MODEL_SERMON_ALGORITHM_DESIGN.md §9.2] Logos Print/Export
# originals live outside DEFAULT_RAW_DIR — they are not primary research
# documents (scripts/check_raw_only_originals.py's RAW-only guard is scoped
# to DEFAULT_RAW_DIR and must not be asked to reason about this directory),
# and are never committed (see .gitignore). DEFAULT_LOGOS_OUTPUT_DIR holds
# the chunked/registered output of scripts/ingest_logos_export.py, kept
# separate from DEFAULT_OUTPUT_DIR's registry so a Logos ingest run cannot
# collide with the main corpus's document_id namespace by directory alone
# (document_id itself is still content-hash based, per core/document_identity.py).
DEFAULT_LOGOS_INBOX_DIR = os.path.join(DATA_DIR, "inbox", "logos_export")
DEFAULT_LOGOS_OUTPUT_DIR = os.path.join(DATA_DIR, "normalized", "logos")

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

# ── Boundary Score model (SPRINT33-C) ───────────────────
# [SPRINT33-C Phase 4-C] core.semantic_boundary_detector.
# ScriptureReferenceBoundaryFeature only counts a scripture reference that
# appears within a candidate's first N characters as a boundary signal —
# Phase 4-C's overlap Preflight found that scoring ANY reference found
# anywhere in a candidate would fire on incidental in-body citations
# (~78.5% of ref-bearing, heading-unmatched candidates sampled), not just
# genuine section-title-shaped ones. HQ-set value: 50.
SCRIPTURE_REFERENCE_HEAD_WINDOW = 50
# [SPRINT33-C Phase 5-B] Calibrated down from the Phase 4-C initial value
# (60.0) after Phase 5-A's weight x threshold shadow matrix showed 60.0
# let paragraph(+30) + scripture_reference alone reach 90 -- comfortably
# above DEFAULT_THRESHOLD(50) with no heading corroboration at all, which
# Phase 4-C Validation's manual review linked to the weakest-precision
# match class (20-40% true-boundary rate, dominated by incidental
# citations and WBC-style running-header repeats). The matrix showed the
# decision is flat for any weight in [20, 60] at threshold=50 (paragraph +
# weight must drop under 50 to matter) -- 15.0 was chosen as the first
# value clearly inside that effective range (paragraph(30) + 15 = 45,
# below threshold) while still allowing a scripture reference to
# contribute when reinforced by a second signal (e.g. + sentence_boundary
# = 55, still >= threshold). DEFAULT_THRESHOLD(50) itself is unchanged
# (Phase 5-B scope, HQ Task Order).
SCRIPTURE_REFERENCE_WEIGHT = 15.0

# [ADR-008 제안 3, 2026-07-21] core.semantic_boundary_detector.
# EmbeddingSimilarityBoundaryFeature — 인접 후보 텍스트 임베딩(bge-m3,
# core/embedder.py::get_embedder() 재사용)의 코사인 유사도가 이 값
# 미만이면 주제 전환(경계 신호)으로 본다. Profile B(학력 밀도 낮은
# 학술 주석서)의 Axis 2(semantic flush ratio) 16.4%가 프로덕션 전환에
# 불충분하다는 ADR-008 §1 판정에 대응하는 신규 feature.
#
# [재보정, 2026-07-21] 최초 설계 초안값 0.5는 실측 분포(Profile B
# 4개 문서, n=7055 인접 후보쌍, get_embedder()의 실제 bge-m3 경로로
# 재계산)의 중앙값(0.5615)보다 낮아 오히려 인접 후보 절반 가까이를
# 경계로 판정하는 반대 방향 문제가 있었다(get_embedder() 대신 항상
# 실패하던 legacy embed() 버그를 고친 뒤 드러남). p15 근처로 하향
# 재보정 — 급격한 주제 전환(하위 ~15%)만 신호로 잡는다.
#   실측: p1=0.270 p5=0.333 p10=0.379 p20=0.441 p25=0.470
#         median=0.562 p75=0.638 p90=0.702
EMBEDDING_SIMILARITY_DROP_THRESHOLD = 0.41
EMBEDDING_SIMILARITY_WEIGHT = 40.0

# [SPRINT34 Option A, 2026-07-28, hierarchical-chunk-builder-improvement-
# design.md §3 Option A] Profile B(학술 주석서, heading 드묾)의 Axis 2
# (semantic flush ratio) 23.9%가 임계값 25% 미달 — 긴 문단에서 인접
# candidate 임베딩 유사도가 자연히 높아 EMBEDDING_SIMILARITY_DROP_THRESHOLD
# 신호가 거의 안 남는 문제 대응.
# [주의 — 방향 수정, 2026-07-28] score()는 similarity < threshold일 때
# boundary(1.0)를 낸다 — threshold가 높을수록 더 많은 유사도 값이 걸려
# boundary가 더 "관대하게" 잡힌다. 따라서 버퍼가 safety_cap에
# 가까워질수록 threshold를 DYNAMIC_THRESHOLD_SLOPE 비율만큼 "올려야"
# Profile B에서 boundary를 더 잡는다는 목표에 맞다(설계 문서 초안은 반대
# 방향(하향)으로 적혀 있었으나 그러면 버퍼가 찰수록 오히려 boundary가 덜
# 잡히는 반대 효과가 나 구현 시 수정함). 상한(DYNAMIC_THRESHOLD_CEILING_
# RATIO)으로 과도한 상향을 방지. 계수는 미검증 — Phase 1.4
# canary(scripts/shadow_boundary_delta.py)로 확정 전까지 잠정값.
DYNAMIC_THRESHOLD_SLOPE = 0.3
DYNAMIC_THRESHOLD_CEILING_RATIO = 1.0 + DYNAMIC_THRESHOLD_SLOPE

# n-gram(문자 3-gram) 중복률을 임베딩 유사도와 결합 — 임베딩 실패/저신호
# 상황에서도 표층 반복 여부로 보완 신호를 낸다. alpha는 임베딩 비중.
EMBEDDING_NGRAM_ALPHA = 0.7
EMBEDDING_NGRAM_SIZE = 3

# [ADR-011 제안 3, 2026-07-23] PageHeaderArtifactFeature — 문서 전체에
# 걸쳐 반복되는 running header(페이지 번호만 바뀌는 동일 텍스트)가
# "새로운 semantic 신호"처럼 잘못 인식돼 Axis 3(unsplittable outlier)를
# 왜곡하는 문제(Profile B 최악 사례 "2 Kings, Volume 13", ADR-008
# §Context)에 대응. core.repetition_detector.RepetitionTracker가
# is_repeat=True를 신호하면 "boundary 아님"을 뜻하는 음의 가중치를
# 적용 — tiny_fragment(-60.0)와 동일 계열. 7번째 feature이지만
# _default_registry()에는 아직 등록하지 않음(dormant, ADR-011이
# 구현만 승인, 프로덕션 연결은 별도 승인 대상).
PAGE_HEADER_ARTIFACT_WEIGHT = -60.0

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
DEFAULT_GEN_MODEL = _yaml_ollama.get("default_gen_model", "my-theology-bot-v2:latest")
EMBED_MODEL_OPTIONS = _yaml_ollama.get("embed_model_options", ["bge-m3:latest", "nomic-embed-text", "mxbai-embed-large"])
GEN_MODEL_OPTIONS = _yaml_ollama.get("gen_model_options", ["my-theology-bot-v2:latest", "llama3.1:8b", "llama3:latest"])

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
