"""core/processing.py — 연구용 청킹 파이프라인 (업그레이드 v2)

추가 기능:
1. [NEW] 출 력 검증 (validate_chunks()) — 청크 유효성 검사 강화
2. [NEW] 리트라이 로직 (process_with_retry()) — 실패 시 3회 재시도
3. [NEW] 배치 상태 관리 (BatchState) — 중단 후 재시작 지원
"""

from __future__ import annotations

import os
import json
import shutil
import traceback
import logging
import datetime
import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TypeVar, Callable

from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, EasyOcrOptions
from langchain_text_splitters import SentenceTransformersTokenTextSplitter

from core.extractors import extract_text_from_file
from core.utils import make_safe_stem, calculate_noise_score
from core.chunking_optimizer import optimize_chunks, save_optimized_md
from core.text_normalizer import reflow_wrapped_lines
from core.frontmatter_detector import split_front_matter

# [PT-PROCESSING-008] Document identity integration
from core.document_identity import (
    generate_document_id,
    compute_content_hash,
    generate_chunk_id,
    build_document_metadata,
    generate_processing_timestamp,
)

# [SPRINT17-Phase1-B-2] DocumentContext — additive only, not yet wired into
# metadata/registry flow (see docs/architecture/DBMA-SPRINT17-Implementation-Plan-v1.md Phase 2)
from core.document_context import DocumentContext

# [PT-PROCESSING-010/012] Identity registry + incremental ingest
from core.identity_registry import (
    load_identity_registry,
    register_document,
    save_identity_registry,
    find_by_document_id,
    find_by_file_hash,
    classify_ingest_decision,
    update_content_hash,
    transition_ingest_status,
    update_pipeline_flags,
)
from core.config import registry_path_for

logger = logging.getLogger(__name__)

_splitter_cache: dict[tuple[int, int], Any] = {}

# ── 상수 ────────────────────────────────────────────────
MAX_RETRY = 3               # 리트라이 최대 횟수
RETRY_DELAY_SEC = 2.0       # 재시도 간격 (초)
MIN_CHUNK_CHARS = 80        # 최소 청크 길이
# ── SPRINT 1 OUTPUT STANDARDIZATION ───────────────────────
SPRINT1_ONLY_MD_OUTPUT = False   # Sprint 1: ONLY .md is canonical output
OUTPUT_VALIDATE_ENABLED = True  # 출력 검증 활성화


# ── 데이터클래스 ────────────────────────────────────────

@dataclass
class BatchState:
    """배치 처리 상태 추적 — 중단 후 재시작"""
    output_dir: str
    state_file: Optional[Path] = field(default=None)  # runtime에서 설정
    processed: List[str] = field(default_factory=list)
    failed: List[str] = field(default_factory=list)

    def __post_init__(self):
        if self.state_file is None:
            self.state_file = Path(self.output_dir) / ".batch_state.json"

    def save(self):
        if self.state_file is None:
            self.state_file = Path(self.output_dir) / ".batch_state.json"
        data = {
            "processed": self.processed,
            "failed": self.failed,
            "timestamp": datetime.datetime.now().isoformat(),
        }
        self.state_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, output_dir: str) -> "BatchState":
        state_file = Path(output_dir) / ".batch_state.json"
        if state_file.exists():
            data = json.loads(state_file.read_text(encoding="utf-8"))
            return cls(output_dir=output_dir, processed=data.get("processed", []), failed=data.get("failed", []))
        return cls(output_dir=output_dir, processed=[], failed=[])


@dataclass
class ChunkValidationResult:
    """청크 출력 검증 결과"""
    valid: bool
    total_chunks: int
    filtered_short: int
    filtered_empty: int
    encoding_errors: int
    reasons: List[str] = field(default_factory=list)

    def summary(self) -> str:
        return (
            f"valid={self.valid}, total={self.total_chunks}, "
            f"filtered(short={self.filtered_short}, empty={self.filtered_empty}), "
            f"encoding_err={self.encoding_errors}"
        )


# ── 유틸리티 ───────────────────────────────────────────

def build_converter(use_ocr: bool = False) -> DocumentConverter:
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = bool(use_ocr)
    if use_ocr:
        pipeline_options.ocr_options = EasyOcrOptions()
    return DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)}
    )


def build_splitter(chunk_size: int, chunk_overlap: int) -> SentenceTransformersTokenTextSplitter:
    """캐시 추가: 동일 파라미터면 재사용"""
    cache_key = (chunk_size, chunk_overlap)
    if cache_key not in _splitter_cache:
        _splitter_cache[cache_key] = SentenceTransformersTokenTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            model_name="BAAI/bge-m3",
        )
    return _splitter_cache[cache_key]


def detect_language(text: str) -> str:
    if not text:
        return "en"

    total_chars = len([c for c in text if c.strip()])  # 공백 제외 문자 수

    hangul_chars = sum(1 for c in text if '\uAC00' <= c <= '\uD7A3')        # 한글 음절
    hangul_jamo  = sum(1 for c in text if '\u1100' <= c <= '\u11FF')        # 한글 자모(선택)
    japanese_chars = sum(1 for c in text if ('\u3040' <= c <= '\u309F') or  # 히라가나
                                            ('\u30A0' <= c <= '\u30FF'))    # 가타카나
    chinese_chars = sum(1 for c in text if '\u4E00' <= c <= '\u9FFF')       # CJK 한자
    hebrew_chars  = sum(1 for c in text if '\u0590' <= c <= '\u05FF')       # 히브리어
    greek_chars   = sum(1 for c in text if '\u0370' <= c <= '\u03FF')       # 그리스어

    if total_chars == 0:
        return "en"

    # 비율 기준으로 우선순위 판단
    if (hangul_chars + hangul_jamo) / total_chars > 0.1:
        return "ko"
    elif japanese_chars / total_chars > 0.1:
        return "ja"
    elif chinese_chars / total_chars > 0.1:
        return "zh"
    elif hebrew_chars / total_chars > 0.1:
        return "he"
    elif greek_chars / total_chars > 0.1:
        return "el"

    return "en"


# ── [NEW #3] 출력 검증 ─────────────────────────────────

def validate_chunks(
    chunks: List[str],
    meta: Dict[str, Any],
    min_chars: int = MIN_CHUNK_CHARS,
) -> ChunkValidationResult:
    """청크 출력物을 검증합니다.

    검증 항목:
    - 빈 청크 필터링
    - 최소 길이 미만 필터링
    - 인코딩 오류 검사 (UTF-8)
    - 메타 데이터 정합성 (chunks 수 일치)
    """
    if not chunks:
        return ChunkValidationResult(
            valid=False, total_chunks=0, filtered_short=0,
            filtered_empty=0, encoding_errors=0, reasons=["chunks is empty"],
        )

    filtered_short = 0
    filtered_empty = 0
    encoding_errors = 0
    valid_chunks = []

    for i, ch in enumerate(chunks):
        # 빈 청크 검사
        if not ch or not ch.strip():
            filtered_empty += 1
            continue

        # 인코딩 검사
        try:
            ch.encode("utf-8")
        except UnicodeEncodeError:
            encoding_errors += 1
            continue

        # 최소 길이 검사
        if len(ch.strip()) < min_chars:
            filtered_short += 1
            continue

        valid_chunks.append(ch)

    # 메타 데이터 정합성
    meta_chunks_count = meta.get("chunks", 0)
    meta_consistent = (meta_chunks_count == len(chunks))

    valid = (filtered_empty == 0 and encoding_errors == 0 and meta_consistent)
    reasons = []
    if filtered_empty > 0:
        reasons.append(f"{filtered_empty} empty chunks filtered")
    if encoding_errors > 0:
        reasons.append(f"{encoding_errors} encoding errors")
    if not meta_consistent:
        reasons.append(f"meta mismatch: meta={meta_chunks_count}, actual={len(chunks)}")

    return ChunkValidationResult(
        valid=valid, total_chunks=len(chunks),
        filtered_short=filtered_short, filtered_empty=filtered_empty,
        encoding_errors=encoding_errors, reasons=reasons,
    )


_R = TypeVar("_R")


# ── [NEW #1] 리트라이 로직 ─────────────────────────────

def _retry_with_backoff(func: Callable[..., _R], *args, max_retries: int = MAX_RETRY, delay: float = RETRY_DELAY_SEC, **kwargs) -> _R:
    """지수 백오프 재시도 데코레이터風 함수"""
    last_exc: Optional[Exception] = None
    for attempt in range(1, max_retries + 1):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_exc = e
            if attempt < max_retries:
                wait_time = delay * (2 ** (attempt - 1))
                logger.warning(
                    "Retry %d/%d failed for %s: %s. Retrying in %.1fs...",
                    attempt, max_retries, func.__name__, e, wait_time,
                )
                time.sleep(wait_time)
            else:
                logger.error(
                    "All %d retries exhausted for %s. Last error: %s",
                    max_retries, func.__name__, last_exc,
                )
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("Unexpected state: retry function returned without success or exception")


# ── 파일 저장 함수들 ───────────────────────────────────

def save_md_with_language(output_dir, stem, source_name, text, noise, source_type, language, document_meta=None):
    """Save markdown with language metadata"""
    path = os.path.join(output_dir, f"{stem}.md")

    # Build frontmatter with basic metadata
    frontmatter = [
        "---",
        f"source: {source_name}",
        f"source_type: {source_type}",
        f"language: {language}",
        f"created_at: {datetime.datetime.now().isoformat()}",
        f"noise_score: {noise['score']}",
        f"noise_mode: {noise.get('mode', '-')}",
    ]

    # Add document metadata fields if available
    if document_meta:
        for key, value in document_meta.items():
            if key in ["title", "author", "book", "chapter", "page", "batch_id"]:
                if value is not None and value != "":
                    frontmatter.append(f"{key}: {value}")

    frontmatter.extend([
        "---",
        "",
        text,
    ])
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(frontmatter))
    return path


# ── SPRINT 1: DEPRECATED OUTPUT FORMATS (kept for backward compat) ──
# These outputs are deprecated for Sprint 1. Use {stem}.md (canonical) instead.
# To re-enable, set SPRINT1_ONLY_MD_OUTPUT = False in config section above.

DEPRECATED_FORMATS_TXT = "chunks_txt"      # DEPRECATED: will be removed in Sprint 2+
DEPRECATED_FORMATS_META = "chunks_meta"    # DEPRECATED: will be removed in Sprint 2+


def save_chunks(output_dir, stem, source_name, chunks, chunk_size, chunk_overlap):
    """[DEPRECATED for Sprint 1] — kept for backward compatibility.

    SPRINT 1 CANONICAL OUTPUT: {stem}.md (produced by save_md_with_language())

    To re-enable these deprecated outputs:
        set SPRINT1_ONLY_MD_OUTPUT = False

    Args:
        output_dir: Output directory path
        stem: Document stem name
        source_name: Original source filename
        chunks: List of chunk strings
        chunk_size: Chunk size parameter
        chunk_overlap: Chunk overlap parameter

    Returns:
        tuple: (txt_path, meta_path) — None paths if SPRINT1_ONLY_MD_OUTPUT is True
    """
    # Sprint 1 compliance: skip deprecated output formats
    if SPRINT1_ONLY_MD_OUTPUT:
        logger.info(
            "[SPRINT1-DEPRECATED] Skipping deprecated outputs for %s (canonical: %s.md)",
            source_name, stem
        )
        return None, None

    txt_path = os.path.join(output_dir, f"{stem}_chunks.txt")
    meta_path = os.path.join(output_dir, f"{stem}_chunks_meta.json")

    # 검증 수행
    meta = {
        "source": source_name,
        "chunks": len(chunks),
        "chunk_size": chunk_size,
        "chunk_overlap": chunk_overlap,
    }
    validation = validate_chunks(chunks, meta)

    if not validation.valid:
        logger.warning("Chunks validation warnings: %s", validation.summary())

    # 유효한 청크만 저장
    with open(txt_path, "w", encoding="utf-8") as f:
        for i, ch in enumerate(chunks, 1):
            f.write(f"[chunk {i}]\n{ch}\n\n")

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    return txt_path, meta_path


def copy_source_file(src_path, output_dir):
    """[SAFETY] Copy source file to output dir — NEVER move/delete originals.

    Sprint 2 policy: Original research documents must NEVER be moved or deleted.
    Processing copies files; RAW originals remain untouched.
    Metadata relationship is tracked in identity registry via source_file field.

    Args:
        src_path: Path to the original source file
        output_dir: Output directory where copy will be placed

    Returns:
        str: Path to the copied file in output_dir (always returns new path)
    """
    dst = os.path.join(output_dir, os.path.basename(src_path))
    if os.path.abspath(src_path) != os.path.abspath(dst):
        # Use copy2 to preserve metadata (timestamps, etc.)
        shutil.copy2(src_path, dst)
    return dst


# ── [NEW #2] 배치 상태 관리 ─────────────────────────────

def get_processed_files(output_dir: str) -> set[str]:
    """이미 처리된 파일 목록을 반환 (중복 처리 방지)"""
    state_file = Path(output_dir) / ".batch_state.json"
    if state_file.exists():
        data = json.loads(state_file.read_text(encoding="utf-8"))
        return set(data.get("processed", []))
    return set()


def mark_processed(output_dir: str, filename: str):
    """처리 완료 파일을 기록"""
    state_file = Path(output_dir) / ".batch_state.json"
    data = {}
    if state_file.exists():
        data = json.loads(state_file.read_text(encoding="utf-8"))

    processed = data.get("processed", [])
    if filename not in processed:
        processed.append(filename)
    data["processed"] = processed
    data["timestamp"] = datetime.datetime.now().isoformat()

    state_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ── 핵심 처리 함수 ─────────────────────────────────────

def process_one_file(file_info, converter, splitter, output_dir, chunk_size, chunk_overlap, report=None):
    """단일 파일 처리 (업그레이드 v2 — 검증 + 리트라이 + 배치 상태)"""
    logs = []
    metrics = {}
    artifacts = {}
    failed_stage = None
    reason = None

    def emit(stage, message, progress=None, level="info"):
        if report is not None:
            report(stage=stage, message=message, progress=progress)
        cls = "log-ok" if level == "ok" else "log-warn" if level == "warn" else "log-info"
        logs.append({"cls": cls, "msg": message})

    src_path = file_info["path"]
    source_name = file_info["name"]
    ext = file_info["ext"].lower().replace(".", "")
    stem = make_safe_stem(source_name)

    try:
        # [SPRINT15-DEBUG] ENTER process_one_file — 첫 진입 지점
        logger.info("[SPRINT15-DEBUG] ENTER process_one_file START | file=%s path=%s", source_name, src_path)
        emit("start", f"process_one_file 시작: {source_name}", 0.0, level="ok")

        use_ocr = bool(file_info.get("use_ocr", False))

        # ── [1] 텍스트 추출 (리트라이) ──────────────────────
        emit("extract", f"텍스트 추출 시작: {source_name}", 0.1)

        # [SPRINT15-DEBUG] extract_text_from_file 호출 전
        logger.info("[SPRINT15-DEBUG] BEFORE extract_text_from_file | file=%s", source_name)

        def _extract():
            return extract_text_from_file(src_path, converter=converter, use_ocr=use_ocr)

        raw_result = _retry_with_backoff(_extract, max_retries=MAX_RETRY)

        # [SPRINT15-DEBUG] extract_text_from_file 호출 후 (성공)
        logger.info("[SPRINT15-DEBUG] AFTER extract_text_from_file SUCCESS | file=%s result_keys=%s", source_name, list(raw_result.keys()) if raw_result else "None")

        full_text = raw_result.get("text", "") or ""
        is_ocr = raw_result.get("is_ocr", use_ocr)
        # [SPRINT17-Phase5-C2] M2-a — title/author from the source file's own
        # embedded metadata (PDF docinfo / DOCX core_properties), when present.
        extracted_title = raw_result.get("title")
        extracted_author = raw_result.get("author")

        # [SPRINT15-DEBUG] extract success/fail 구분
        if full_text:
            logger.info("[SPRINT15-DEBUG] extract_text_from_file SUCCESS | file=%s text_len=%d", source_name, len(full_text))
        else:
            logger.warning("[SPRINT15-DEBUG] extract_text_from_file RETURNED EMPTY TEXT | file=%s raw_result=%s", source_name, raw_result)

        emit("extract_done", f"텍스트 추출 완료: {len(full_text)} characters", 0.2)

        language = detect_language(full_text)
        logger.info("[SPRINT1] parsing completed: %s (%d chars, lang=%s)", source_name, len(full_text), language)
        emit("language", f"감지된 언어: {language}", 0.25)

        if not full_text.strip():
            failed_stage = "extract"
            reason = "추출 텍스트 없음"
            emit("extract_fail", f"{source_name}: 추출 텍스트 없음", 1.0, level="warn")
            return {"success": False, "logs": logs, "metrics": metrics, "artifacts": artifacts, "failed_stage": failed_stage, "reason": reason}

        # ── [1.5] 전면부(제목/판권/목차) 분리 ────────────────
        # Noise scoring and chunking below run on body_text only — front
        # matter (title/copyright/TOC pages) has structurally different
        # characteristics (dense short lines, boilerplate) that either
        # drags a whole document's noise score up or gets diluted into
        # invisibility once averaged across a large body, neither of
        # which reflects actual body content quality. Front matter is
        # still saved in the .md (see [3] below) for provenance — not
        # discarded, just excluded from scoring/chunking.
        front_matter_text, body_text = split_front_matter(full_text)
        if front_matter_text:
            emit("frontmatter", f"전면부 감지: {len(front_matter_text)}자 (본문 {len(body_text)}자)", 0.28)
            logger.info("[FRONTMATTER] detected: %s (front=%d chars, body=%d chars)", source_name, len(front_matter_text), len(body_text))

        # ── [2] 노이즈 분석 ────────────────────────────────
        emit("noise", f"노이즈 점검 시작: {source_name}", 0.3)

        # [SPRINT15-DEBUG] calculate_noise_score 호출 전
        logger.info("[SPRINT15-DEBUG] BEFORE calculate_noise_score | file=%s text_len=%d", source_name, len(body_text))

        noise = calculate_noise_score(body_text, file_type=ext, is_ocr=is_ocr)

        # [SPRINT15-DEBUG] calculate_noise_score 호출 후
        logger.info("[SPRINT15-DEBUG] AFTER calculate_noise_score SUCCESS | file=%s noise_score=%s", source_name, noise.get("score", "N/A") if noise else "None")

        emit("noise_done", f"노이즈 점검 완료: score={noise['score']}", 0.4)
        logs.append({
            "cls": "log-info",
            "msg": (f"noise_debug: mode={noise['mode']}, score={noise['score']}, "
                    f"chars={noise['charcount']}, symbol={noise['symbol_ratio']}, "
                    f"short={noise['short_line_ratio']}, ocr={noise['ocr_noise_ratio']}"),
        })

        final_text = full_text
        if not final_text.strip():
            failed_stage = "noise"
            reason = "정제 후 텍스트 없음"
            emit("noise_fail", f"{source_name}: 정제 후 텍스트 없음", 1.0, level="warn")
            return {"success": False, "logs": logs, "metrics": metrics, "artifacts": artifacts, "failed_stage": failed_stage, "reason": reason}

        # ── [PT-PROCESSING-008] Document Identity Generation (Point A) ──
        document_id = generate_document_id(content=final_text, source_file=source_name)
        file_hash = compute_content_hash(final_text)
        emit("identity", f"Document identity: {document_id[:16]}...", 0.42)

        # [SPRINT17-Phase1-B-2] DocumentContext instance — created for future
        # Phase 2 wiring only. Not read anywhere below in this function yet;
        # build_document_metadata()/registry flow remain the source of truth.
        _document_context = DocumentContext(
            document_id=document_id,
            file_hash=file_hash,
            source_file=source_name,
            source_type=ext,
            is_ocr=is_ocr,
            title=extracted_title,
            author=extracted_author,
        )
        # [SPRINT21-B Phase1] identity generated (doc_id/file_hash), chunking
        # not yet run — matches the IDENTIFIED state definition.
        _document_context.pipeline_state = "IDENTIFIED"

        # ── [PT-PROCESSING-012] Incremental ingest decision gate ────
        registry_path = registry_path_for(output_dir)
        _registry = load_identity_registry(registry_path)

        # Pre-processing: classify ingest decision (PROCESS/SKIP/REPROCESS/RETRY)
        decision, existing_record = classify_ingest_decision(_registry, document_id, file_hash)

        if decision == "SKIP":
            _prev_src = existing_record.get("source_file", "") if existing_record else ""
            emit("skip", f"UNCHANGED: {_prev_src or source_name}", 1.0, level="ok")

            # [SPRINT17-Phase2-C] Synchronize DocumentContext from existing
            # registry data on the SKIP path — this branch never runs the
            # PROCESS-path sync block below, so without this the context
            # would stay frozen at its Point A construction values. Read-only
            # copy from existing_record; does not write back to the registry.
            if existing_record:
                _document_context.title = existing_record.get("title")
                _document_context.author = existing_record.get("author")
                _document_context.book = existing_record.get("book")
                _document_context.chapter = existing_record.get("chapter")
                _document_context.page = existing_record.get("page")
                _document_context.batch_id = existing_record.get("batch_id")
                _document_context.language = existing_record.get("language", _document_context.language)
                _document_context.noise_score = existing_record.get("noise_score", _document_context.noise_score)
                _document_context.noise_mode = existing_record.get("noise_mode", _document_context.noise_mode)
                _document_context.chunk_count = existing_record.get("chunk_count", _document_context.chunk_count)
                _document_context.ingest_status = existing_record.get("ingest_status", _document_context.ingest_status)
                _document_context.retry_count = existing_record.get("retry_count", _document_context.retry_count)
                _document_context.last_failure_reason = existing_record.get("last_failure_reason")
                if "pipeline_flags" in existing_record:
                    _document_context.pipeline_flags = dict(existing_record["pipeline_flags"])
                # [SPRINT21-B Phase1] SKIP means content unchanged — carry the
                # document's actual pipeline_state forward (may already be
                # TSU_READY/INDEXED) rather than resetting it.
                _document_context.pipeline_state = existing_record.get("pipeline_state", "PROCESSED")
            # [FIX] Ensure markdown output exists for SKIP documents — save if not already present
            md_output_dir = Path(output_dir)
            md_output_dir.mkdir(parents=True, exist_ok=True)
            _md_path = md_output_dir / f"{stem}.md"
            _prev_hash = existing_record.get("content_hash", "") if existing_record else ""
            if not _md_path.exists() or file_hash != _prev_hash:
                # For SKIP case, reuse existing metadata fields to preserve title, author, chapter, page
                _fm = [
                    "---",
                    f"source: {source_name}",
                    f"source_type: {ext}",
                    f"language: {language}",
                    f"created_at: {datetime.datetime.now().isoformat()}",
                    f"noise_score: {noise['score']}",
                    f"noise_mode: {noise.get('mode', '-')}",
                ]

                # Add document metadata fields from existing record if available
                if existing_record:
                    for key in ["title", "author", "book", "chapter", "page", "batch_id"]:
                        if key in existing_record and existing_record[key] is not None and existing_record[key] != "":
                            _fm.append(f"{key}: {existing_record[key]}")

                _fm.extend([
                    "---",
                    "",
                    final_text,
                ])
                _md_path.write_text("\n".join(_fm), encoding="utf-8")
            artifacts = {**artifacts, "md_path": str(_md_path)}
            return {"success": True, "skipped": True, "ingest_decision": "SKIP", "logs": logs, "metrics": metrics, "artifacts": artifacts}

        if decision == "RETRY":
            _prev_retries = existing_record.get("retry_count", 0) if existing_record else 0
            emit("retry", f"Retry ingest (attempt {_prev_retries + 1}/3)", 1.0, level="warn")

        if decision == "REPROCESS":
            _prev_src = existing_record.get("source_file", "") if existing_record else ""
            emit("reprocess", f"MODIFIED content detected (reprocessing): {_prev_src or source_name}", 1.0, level="warn")


        # ── [3] MD 저장 ────────────────────────────────────
        emit("save_md", f"MD 저장 시작: {source_name}", 0.5)
        # Reflow PDF-style mid-sentence line wraps for readability in the
        # saved .md body. Deliberately NOT applied to final_text itself —
        # chunking below uses body_text unchanged (see reflow_wrapped_lines
        # docstring for why the two are kept independent).
        # Front matter (if detected) is kept in the saved .md for
        # provenance/citation, clearly demarcated and reflowed separately,
        # but is not part of what gets noise-scored or chunked above.
        if front_matter_text:
            md_display_text = (
                "## 전면부 (제목/판권/목차 — 검색·노이즈 채점 대상 제외)\n\n"
                + reflow_wrapped_lines(front_matter_text)
                + "\n\n---\n\n## 본문\n\n"
                + reflow_wrapped_lines(body_text)
            )
        else:
            md_display_text = reflow_wrapped_lines(body_text)

        # [SPRINT15-DEBUG] save_md_with_language 호출 전
        logger.info("[SPRINT15-DEBUG] BEFORE save_md_with_language | file=%s output_dir=%s stem=%s", source_name, output_dir, stem)

        # [PT-PROCESSING-008] Complete Document Metadata (Point C) - define before use
        document_meta = build_document_metadata(
            content=final_text, source_file=source_name,
            language=language, noise_score=noise["score"],
            noise_mode=noise.get("mode", "-"), source_type=ext,
            is_ocr=is_ocr, chunk_count=0,  # Will be updated after chunking
            title=extracted_title, author=extracted_author,
        )

        md_path = save_md_with_language(output_dir, stem, source_name, md_display_text, noise, ext, language, document_meta)

        # [SPRINT15-DEBUG] save_md_with_language 호출 후
        logger.info("[SPRINT15-DEBUG] AFTER save_md_with_language SUCCESS | file=%s md_path=%s", source_name, md_path)

        # [SPRINT15-DEBUG] 실제 MD 파일 존재 확인
        md_exists = os.path.isfile(md_path) if md_path else False
        logger.info("[SPRINT15-DEBUG] MD file exists check | file=%s path=%s exists=%s", source_name, md_path, md_exists)
        emit("save_md_done", f"MD 저장 완료: {md_path}", 0.55)

        # ── [4] 청킹 (리트라이) ────────────────────────────
        emit("chunk", f"청킹 시작: {source_name}", 0.65)

        # [SPRINT15-DEBUG] optimize_chunks 호출 전
        logger.info("[SPRINT15-DEBUG] BEFORE optimize_chunks | file=%s text_len=%d", source_name, len(body_text))

        def _chunk():
            return optimize_chunks(body_text, ext)

        try:
            chunk_result = _retry_with_backoff(_chunk, max_retries=MAX_RETRY)
            chunks = chunk_result.chunks if getattr(chunk_result, "chunks", None) else []
        except Exception as e:
            logs.append({"cls": "log-warn", "msg": f"optimize_chunks 실패 (리트라이 후): {e}"})
            chunk_result = None
            chunks = []

        if chunk_result is not None:
            logs.append({
                "cls": "log-info",
                "msg": (f"chunk_debug: passed={chunk_result.passed}, "
                        f"avg_noise={chunk_result.quality.avg_noise:.2f}, "
                        f"max_noise={chunk_result.quality.max_noise:.2f}, "
                        f"avg_dup={chunk_result.quality.avg_dup:.2f}, "
                        f"params={chunk_result.params}"),
            })

        # [SPRINT15-DEBUG] optimize_chunks 호출 후 (성공/실패 구분)
        if chunk_result is not None and getattr(chunk_result, "chunks", None):
            logger.info("[SPRINT15-DEBUG] AFTER optimize_chunks SUCCESS | file=%s chunk_count=%d", source_name, len(chunk_result.chunks))
        else:
            logger.warning("[SPRINT15-DEBUG] AFTER optimize_chunks NO CHUNKS | file=%s chunk_result=%s", source_name, chunk_result)

        if not chunks:
            emit("fallback_split", f"옵티마이저 결과 없음, 기존 splitter 사용: {source_name}", 0.78, level="warn")
            chunks = splitter.split_text(body_text)
            chunk_size_used = chunk_size
            chunk_overlap_used = chunk_overlap
            chunk_result = None
        elif chunk_result is not None:
            chunk_size_used = chunk_result.params["chunk_size"]
            chunk_overlap_used = chunk_result.params["chunk_overlap"]
        else:
            chunk_size_used = chunk_size
            chunk_overlap_used = chunk_overlap

        emit("chunk_done", f"청킹 완료: {len(chunks)} chunks", 0.75)
        logger.info("[SPRINT1] chunking completed: %s (%d chunks, size=%d, overlap=%d)", source_name, len(chunks), chunk_size_used, chunk_overlap_used)

        # ── [PT-PROCESSING-008] Chunk ID Assignment (Point B) ──
        chunk_ids = [generate_chunk_id(document_id, idx) for idx in range(len(chunks))]
        emit("identity", f"Chunk IDs assigned: {len(chunk_ids)}", 0.76)

        # ── [5] 청크 저장 + 검증 ───────────────────────────
        meta = {"source": source_name, "chunks": len(chunks), "chunk_size": chunk_size_used, "chunk_overlap": chunk_overlap_used}
        emit("validate", f"청크 검증 시작: {source_name}", 0.79)
        validation = validate_chunks(chunks, meta)
        emit("validate_done", f"청크 검증 결과: {validation.summary()}", 0.80)

        txt_path, meta_path = save_chunks(output_dir, stem, source_name, chunks, chunk_size_used, chunk_overlap_used)
        if SPRINT1_ONLY_MD_OUTPUT:
            emit("save_chunks_done", f"[SPRINT1-DEPRECATED] Deprecated outputs skipped (canonical: {stem}.md)", 0.85)
        else:
            emit("save_chunks_done", f"기존 txt 저장 완료: {source_name}", 0.85)

        # ── [6] 최적화 MD 저장 (SPRINT1-DEPRECATED) ───────────
        # Sprint 1 canonical output is ONLY {stem}.md (save_md_with_language).
        # Optimized chunks markdown ({stem}_chunks_{hash}.md) is deprecated for Sprint 1.
        opt_md_path = None
        emit("save_opt_md", f"[SPRINT1-DEPRECATED] 최적화 MD 저장 건너뜀 (canonical: {stem}.md)", 0.9)

        # ── [7] 원본 파일 복사 + 배치 상태 기록 (Sprint 2 policy: NEVER move/delete originals) ────
        emit("copy", f"원본 파일 복사 시작: {source_name}", 0.97)
        copied_to = copy_source_file(src_path, output_dir)
        mark_processed(output_dir, source_name)
        emit("copy_done", f"원본 파일 복사 완료: {copied_to} (원본은 RAW에 유지)", 0.99)

        # ── [PT-PROCESSING-008] Complete Document Metadata (Point C) ──
        # [SPRINT17-Phase1-B-3b] Sync finalized fields into DocumentContext
        # before it becomes the metadata source below (Phase2-A Step 1).
        _document_context.language = language
        _document_context.noise_score = noise["score"]
        _document_context.noise_mode = noise.get("mode", "-")
        _document_context.source_type = ext
        _document_context.is_ocr = is_ocr
        _document_context.chunk_count = len(chunks)
        # [SPRINT21-B Phase1] extraction + chunking complete.
        _document_context.pipeline_state = "EXTRACTED"
        # [SPRINT17-Phase2-B] registered_at is a distinct concept from
        # created_at (which stays immutable, set once at Point A — see
        # DocumentContext.__post_init__). registered_at marks this specific
        # registration moment and is populated immediately before
        # register_document() below.
        _document_context.registered_at = generate_processing_timestamp()
        # [SPRINT21-B Phase1] about to persist to the registry — TSU/index
        # are separate, not-yet-connected steps (Phase2), so this document
        # stops at PROCESSED here.
        _document_context.pipeline_state = "PROCESSED"

        # [SPRINT17-Phase2-A] DocumentContext is now the metadata source for
        # register_document() — build_document_metadata() is no longer called
        # at this point (still used at Point C-1 for save_md_with_language()).
        document_meta = _document_context.to_metadata_dict()

        # ── [PT-PROCESSING-012] Update content hash on success ──────
        _hash_updated = update_content_hash(_registry, document_id, file_hash)

        # ── [PT-PROCESSING-010-C/012] Persist identity registry ────
        record, is_new = register_document(_registry, document_meta, output_dir)
        persisted_ok = save_identity_registry(_registry, registry_path)

        # ── [SPRINT2] Set pipeline completion flags on successful persist ──
        _pipeline_flags_set = False
        if persisted_ok and record:
            updated = update_pipeline_flags(
                _registry, document_id,
                {"ingested": True, "copied": True, "extracted": True,
                 "cleaned": True, "chunked": True, "output_generated": True,
                 "verified": True},
            )
            if updated:
                save_identity_registry(_registry, registry_path)
                _pipeline_flags_set = True

        if persisted_ok:
            emit("identity_persist", f"Identity registered: {document_id[:16]}..." if is_new else "Identity synced to registry", 0.98)

        metrics = {
            "language": language, "noise": noise, "chunk_count": len(chunks),
            "chunk_size_used": chunk_size_used, "chunk_overlap_used": chunk_overlap_used,
            "chunk_passed": getattr(chunk_result, "passed", None) if chunk_result else None,
            "validation": validation.summary() if OUTPUT_VALIDATE_ENABLED else None,
            "is_ocr": is_ocr, "source_type": ext,
            # [PT-PROCESSING-008] Document identity fields
            "document_id": document_id,
            "file_hash": file_hash,
            "metadata": document_meta,  # Per METADATA_CONTRACT_v1
        }
        artifacts = {
            "source_path": src_path, "copied_path": copied_to, "md_path": md_path,
            "opt_md_path": str(opt_md_path) if opt_md_path else None,
            # [SPRINT1-DEPRECATED] These paths are None when SPRINT1_ONLY_MD_OUTPUT=True
            "chunks_txt_path": txt_path,      # DEPRECATED: None in Sprint 1
            "chunks_meta_path": meta_path,    # DEPRECATED: None in Sprint 1
        }

        # ── [SPRINT1] output written ───────────────────────────
        logger.info("[SPRINT1] output written: %s (canonical=%s)", source_name, md_path)

        # [SPRINT15-DEBUG] END process_one_file — 정상 종료 직전
        logger.info("[SPRINT15-DEBUG] END process_one_file SUCCESS | file=%s md_exists=%s", source_name, md_exists)

        emit("done", f"{source_name} 처리 완료", 1.0, level="ok")
        return {"success": True, "logs": logs, "metrics": metrics, "artifacts": artifacts, "failed_stage": None, "reason": None}

    except Exception as e:
        _failure_reason = str(e)

        # [SPRINT15-DEBUG] 예외 발생 지점 — 어디에서 멈췄는지 확인
        logger.error("[SPRINT15-DEBUG] EXCEPTION CAUGHT | file=%s failed_stage=%s reason=%s", source_name, failed_stage, _failure_reason)
        logger.error("[SPRINT15-DEBUG] Exception traceback | file=%s\n%s", source_name, traceback.format_exc())

        # [PT-PROCESSING-012] Track failure in registry
        # FIXED: Check if document_id and file_hash are defined before using them
        if 'document_id' in locals() and 'file_hash' in locals() and document_id and file_hash:
            try:
                _fail_decision, _fail_record = classify_ingest_decision(_registry, document_id, file_hash)
                if _fail_decision != "PROCESS" and _fail_record is not None:
                    transition_ingest_status(_registry, document_id, "FAILED", failure_reason=_failure_reason)
                    # [SPRINT21-B Phase1] additive; does not touch ingest_status.
                    _fail_record["pipeline_state"] = "FAILED"
                    save_identity_registry(_registry, registry_path)
            except Exception:
                pass  # Don't let registry update failures mask the original error

        logs.append({"cls": "log-warn", "msg": f"처리 실패 — {_failure_reason}"})
        logs.append({"cls": "log-warn", "msg": f"Traceback: {traceback.format_exc()}"})

        # [SPRINT15-DEBUG] 예외 반환 시에도 MD 존재 확인
        md_check_path = os.path.join(output_dir, f"{stem}.md") if 'stem' in locals() else None
        md_exists_at_failure = os.path.isfile(md_check_path) if md_check_path else False
        logger.warning("[SPRINT15-DEBUG] AT FAILURE | file=%s md_path=%s md_exists=%s", source_name, md_check_path, md_exists_at_failure)

        return {"success": False, "logs": logs, "metrics": metrics, "artifacts": artifacts, "failed_stage": failed_stage or "unexpected", "reason": _failure_reason}


def process_batch(file_list, converter, splitter, output_dir, chunk_size, chunk_overlap, report=None):
    """배치 처리 (업그레이드 v2 — 중복 파일 제외 + 배치 상태 추적)"""
    logger.info("[SPRINT1] ingestion start: %d files", len(file_list))
    processed_set = get_processed_files(output_dir)
    results = []

    for file_info in file_list:
        name = file_info.get("name", "")
        if name in processed_set:
            logs = [{"cls": "log-info", "msg": f"이미 처리됨 (건너뜀): {name}"}]
            results.append({"success": True, "logs": logs, "metrics": {}, "artifacts": {}, "skipped": True})
            continue

        result = process_one_file(file_info, converter, splitter, output_dir, chunk_size, chunk_overlap, report)
        results.append(result)

    logger.info("[SPRINT1] ingestion end: %d files processed", len(results))
    return results